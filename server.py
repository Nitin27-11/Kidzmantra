"""Kidzmantra backend.

Serves the website from ./public and answers questions at POST /api/ask
using Claude or Gemini, with web search so it can answer about anything in the world.

Run:  ./run.sh   (reads ANTHROPIC_API_KEY or GEMINI_API_KEY from .env or the environment)
"""

import json
import logging
import os
import time
import struct
from collections import OrderedDict, defaultdict, deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic
import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"


def load_env_file():
    """Load KEY=value lines from .env without needing an extra package."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
MODEL = os.environ.get("KIDZMANTRA_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("KIDZMANTRA_EFFORT", "medium")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-flash-lite-latest")
# Natural "tutor" voice for reading answers aloud.
GEMINI_TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
GEMINI_TTS_FALLBACK_MODEL = os.environ.get("GEMINI_TTS_FALLBACK_MODEL", "gemini-3.8-flash-lite-tts")
GEMINI_VOICE = os.environ.get("GEMINI_VOICE", "Sulafat")

# "claude" or "gemini". If not set, use whichever key is present (Gemini only
# when there is no Anthropic key).
PROVIDER = os.environ.get("AI_PROVIDER", "").strip().lower() or (
    "gemini" if GEMINI_KEY and not os.environ.get("ANTHROPIC_API_KEY") else "claude"
)

# Per-visitor limit so one browser can't run up the API bill.
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "30"))  # questions
RATE_WINDOW = 10 * 60  # seconds

MAX_QUESTION = 1000
MAX_HISTORY = 8
MAX_CONTINUATIONS = 3

client = anthropic.Anthropic()
gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
# Quiet the library's harmless "non-text parts" warning on every answer.
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

SYSTEM_PROMPT = """You are Mantra Buddy, the friendly AI tutor on Kidzmantra, a learning website for school children in India from Nursery to Class 8 (Nursery, LKG, UKG, then Class 1 to 8).

Who you are talking to: a child (sometimes with a parent or teacher). The child's class, and the subject and chapter they are studying, are given below when known. Pitch every answer at that level.

How to answer:
- Start directly with the answer. No greeting (such as "Hello" or "नमस्ते"), no introducing yourself, and no opening praise of the question (such as "Great question!"). The answer is read aloud by a tutor voice, so the first sentence should already teach.
- Use simple, warm, encouraging language. Short sentences. Explain new words.
- For Nursery, LKG, UKG and Class 1 to 2: a few short sentences, very simple words, a fun everyday example.
- For Class 3 to 5: a clear explanation with one or two examples from daily life in India.
- For Class 6 to 8: a fuller explanation with steps, key terms and an example. Show working for maths.
- When asked to quiz, give the questions first and the answers at the end under "Answers".
- Use short bullet points or numbered steps when they help. Do not use tables, headings or code blocks.
- If the child writes in Hindi or Hinglish, answer in the same style.
- If the question is unclear, ask one short clarifying question.
- Help them learn rather than just handing over homework answers: explain how to get there, then give the answer.

Questions about anything in the world are welcome, not only school chapters. Use web search when the answer depends on recent events, specific facts, or things you are not sure about. Never invent facts; if you are unsure, say so simply.

Keeping children safe:
- Keep everything age-appropriate. Do not describe violence, sexual content, self-harm methods, drugs, or anything frightening in detail.
- If a child seems upset, unsafe, or mentions being hurt, respond kindly, tell them it is not their fault, and encourage them to talk to a parent, teacher or another trusted adult. In India they can call 1098 (Childline) any time.
- Never ask for, or encourage sharing, personal details such as full name, address, phone number, school name, or photos.
- Do not link to or recommend websites that are not suitable for children."""

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}

REFUSAL_REPLY = (
    "That's not something I can help with. Let's try a different question, "
    "or ask a parent or teacher about this one!"
)

_hits = defaultdict(deque)


def rate_limited(key, limit=RATE_LIMIT):
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def clean_text(value, limit):
    return value.strip()[:limit] if isinstance(value, str) else ""


def build_messages(history, question):
    """Turn the page's history into strictly alternating user/assistant turns."""
    messages = []
    for item in history[-MAX_HISTORY:] if isinstance(history, list) else []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        text = clean_text(item.get("text"), 6000)
        if role not in ("user", "assistant") or not text:
            continue
        expected = "user" if not messages or messages[-1]["role"] == "assistant" else "assistant"
        if role == expected:
            messages.append({"role": role, "content": text})
    if messages and messages[-1]["role"] == "user":
        messages.pop()
    messages.append({"role": "user", "content": question})
    return messages


def context_note(grade, subject, chapter, lang=""):
    parts = [f"Class: {grade or 'not given'}"]
    if lang == "hi":
        parts.append("Language: the child chose Hindi. Answer in simple Hindi written in Devanagari script; English words for school terms are fine. The answer may be read aloud, so avoid symbols and emojis.")
    elif lang == "en":
        parts.append("Language: the child chose English (if they write in Hindi or Hinglish, answer in the same style). The answer may be read aloud, so avoid symbols and emojis.")
    if subject:
        parts.append(f"Subject: {subject}")
    if chapter:
        parts.append(f"Chapter they are on: {chapter}")
    return "\n".join(parts)


def ask_claude(question, grade, subject, chapter, history, lang=""):
    system = [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "Current learner\n" + context_note(grade, subject, chapter, lang)},
    ]
    messages = build_messages(history, question)

    for _ in range(MAX_CONTINUATIONS + 1):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            output_config={"effort": EFFORT},
            system=system,
            messages=messages,
            tools=[WEB_SEARCH_TOOL],
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason != "pause_turn":
            break
        # Web search paused mid-turn: send the partial turn back so it resumes.
        messages = messages + [{"role": "assistant", "content": response.content}]

    if response.stop_reason == "refusal":
        return {"answer": REFUSAL_REPLY, "sources": []}

    texts, sources, seen = [], [], set()
    for block in response.content:
        if block.type != "text":
            continue
        texts.append(block.text)
        for cite in getattr(block, "citations", None) or []:
            url = getattr(cite, "url", None)
            if url and url not in seen:
                seen.add(url)
                sources.append({"url": url, "title": getattr(cite, "title", None) or url})

    answer = "".join(texts).strip()
    if not answer:
        answer = "Hmm, I couldn't think of a good answer. Can you ask it another way?"
    return {"answer": answer, "sources": sources[:5]}


# Strictest Gemini safety filters, since the users are children.
GEMINI_SAFETY = [
    genai_types.SafetySetting(category=c, threshold=genai_types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE)
    for c in (
        genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    )
]


def gemini_generate(attempts, contents, system=None, **config):
    """Try (model, tools) pairs in order. Free keys have no Google Search quota (429), and busy
    models either return 503 or hang, so each try gets a time limit before stepping down."""
    for i, (model, tools) in enumerate(attempts):
        last = i == len(attempts) - 1
        try:
            return gemini_client.models.generate_content(
                model=model,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system, tools=tools,
                    http_options=genai_types.HttpOptions(timeout=60_000 if last else 20_000),
                    **{"safety_settings": GEMINI_SAFETY, **config},
                ),
            )
        except genai_errors.APIError as e:
            if e.code not in (429, 500, 503, 504) or last:
                raise
        except httpx.TimeoutException:
            if last:
                raise


def ask_gemini(question, grade, subject, chapter, history, lang=""):
    contents = [
        genai_types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[genai_types.Part(text=m["content"])],
        )
        for m in build_messages(history, question)
    ]
    system = SYSTEM_PROMPT + "\n\nCurrent learner\n" + context_note(grade, subject, chapter, lang)
    search = [genai_types.Tool(google_search=genai_types.GoogleSearch())]
    # Step down: search -> no search -> lighter model.
    response = gemini_generate(
        [(GEMINI_MODEL, search), (GEMINI_MODEL, None), (GEMINI_FALLBACK_MODEL, None)], contents, system
    )

    if response.prompt_feedback and response.prompt_feedback.block_reason:
        return {"answer": REFUSAL_REPLY, "sources": []}
    candidate = (response.candidates or [None])[0]
    if candidate is None or candidate.finish_reason in (
        genai_types.FinishReason.SAFETY,
        genai_types.FinishReason.PROHIBITED_CONTENT,
        genai_types.FinishReason.BLOCKLIST,
    ):
        return {"answer": REFUSAL_REPLY, "sources": []}

    sources, seen = [], set()
    grounding = candidate.grounding_metadata
    for chunk in (grounding.grounding_chunks if grounding else None) or []:
        web = chunk.web
        if web and web.uri and web.uri not in seen:
            seen.add(web.uri)
            sources.append({"url": web.uri, "title": web.title or web.uri})

    answer = (response.text or "").strip()
    if not answer:
        answer = "Hmm, I couldn't think of a good answer. Can you ask it another way?"
    return {"answer": answer, "sources": sources[:5]}


TRANSLATE_PROMPT = (
    "You translate answers written for school children. Keep the meaning, the friendly tone, "
    "the line breaks and the bullet or numbered points. Hindi means simple Hindi in Devanagari "
    "script. Reply with only the translation."
)


def translate_text(text, to):
    """Translate an answer into Hindi or English, for listening in the other language."""
    prompt = f"Translate this into {'Hindi' if to == 'hi' else 'English'}:\n\n{text}"
    if PROVIDER == "gemini":
        response = gemini_generate(
            [(GEMINI_MODEL, None), (GEMINI_FALLBACK_MODEL, None)], prompt, TRANSLATE_PROMPT
        )
        return (response.text or "").strip()
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=TRANSLATE_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        return ""
    return "".join(b.text for b in response.content if b.type == "text").strip()


_voice_cache = OrderedDict()  # repeated answers don't use up the voice quota again


def speak_text(text):
    """Turn text (English or Hindi) into WAV audio in a warm tutor voice."""
    if text in _voice_cache:
        _voice_cache.move_to_end(text)
        return _voice_cache[text]
    voice = genai_types.SpeechConfig(
        voice_config=genai_types.VoiceConfig(
            prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=GEMINI_VOICE)
        )
    )
    response = gemini_generate(
        [(GEMINI_TTS_MODEL, None), (GEMINI_TTS_FALLBACK_MODEL, None)],
        # Only the answer itself: any spoken style instruction risked being read out loud. The warm
        # tone comes from the chosen voice, and the page plays it a little slower for children.
        text,
        response_modalities=["AUDIO"], speech_config=voice, safety_settings=None,
    )
    audio = response.candidates[0].content.parts[0].inline_data.data
    if audio[:4] != b"RIFF":  # raw 16-bit 24 kHz PCM: add a WAV header
        audio = (b"RIFF" + struct.pack("<I", 36 + len(audio)) + b"WAVEfmt "
                 + struct.pack("<IHHIIHH", 16, 1, 1, 24000, 48000, 2, 16)
                 + b"data" + struct.pack("<I", len(audio)) + audio)
    _voice_cache[text] = audio
    if len(_voice_cache) > 200:
        _voice_cache.popitem(last=False)
    return audio


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
    }

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_audio(self, audio):
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(audio)

    def do_POST(self):
        if self.path not in ("/api/ask", "/api/translate", "/api/speak"):
            return self.send_json(404, {"error": "Not found"})
        ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        # Reading answers aloud takes a few voice requests per answer, so it gets its own allowance.
        speaking = self.path == "/api/speak"
        if rate_limited((ip, "speak") if speaking else ip, RATE_LIMIT * 5 if speaking else RATE_LIMIT):
            return self.send_json(429, {"error": "You've asked a lot of questions! Take a short break and try again in a few minutes."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 100_000:
                return self.send_json(413, {"error": "That message is too long."})
            data = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Bad request."})

        if PROVIDER == "gemini" and not gemini_client:
            return self.send_json(503, {"error": "The AI isn't set up yet. Add your Gemini API key to the .env file and restart the server."})
        if PROVIDER != "gemini" and not os.environ.get("ANTHROPIC_API_KEY"):
            return self.send_json(503, {"error": "The AI isn't set up yet. Add your Anthropic or Gemini API key to the .env file and restart the server."})

        if speaking:
            if not gemini_client:
                return self.send_json(501, {"error": "The tutor voice needs a Gemini API key."})
            text = clean_text(data.get("text"), 3000)
            if not text:
                return self.send_json(400, {"error": "Bad request."})
            work = lambda: speak_text(text)
        elif self.path == "/api/translate":
            text, to = clean_text(data.get("text"), 6000), data.get("to")
            if not text or to not in ("en", "hi"):
                return self.send_json(400, {"error": "Bad request."})
            work = lambda: {"text": translate_text(text, to) or text}
        else:
            question = clean_text(data.get("question"), MAX_QUESTION)
            if not question:
                return self.send_json(400, {"error": "Please type a question."})
            ask = ask_gemini if PROVIDER == "gemini" else ask_claude
            work = lambda: ask(
                question,
                clean_text(data.get("grade"), 40),
                clean_text(data.get("subject"), 60),
                clean_text(data.get("chapter"), 200),
                data.get("history") or [],
                data.get("lang") if data.get("lang") in ("en", "hi") else "",
            )

        try:
            result = work()
            return self.send_audio(result) if speaking else self.send_json(200, result)
        except anthropic.AuthenticationError:
            self.log_error("Anthropic API key is missing or invalid")
            return self.send_json(500, {"error": "The AI isn't set up yet (API key missing or invalid)."})
        except anthropic.RateLimitError:
            return self.send_json(503, {"error": "Lots of kids are asking right now. Please try again in a minute."})
        except anthropic.APIStatusError as e:
            self.log_error("Anthropic API error %s: %s", e.status_code, e.message)
            return self.send_json(502, {"error": "Mantra Buddy couldn't answer right now. Please try again."})
        except anthropic.APIConnectionError:
            return self.send_json(502, {"error": "Mantra Buddy couldn't connect. Please try again."})
        except genai_errors.APIError as e:
            self.log_error("Gemini API error %s: %s", e.code, e.message)
            if e.code in (400, 401, 403) and "API key" in (e.message or ""):
                return self.send_json(500, {"error": "The AI isn't set up yet (API key missing or invalid)."})
            if e.code in (429, 503):
                return self.send_json(503, {"error": "Lots of kids are asking right now. Please try again in a minute."})
            return self.send_json(502, {"error": "Mantra Buddy couldn't answer right now. Please try again."})
        except httpx.TimeoutException:
            return self.send_json(503, {"error": "Mantra Buddy is taking too long right now. Please try again in a minute."})
        except Exception as e:  # e.g. no API key configured at all
            self.log_error("Unexpected error: %r", e)
            return self.send_json(500, {"error": "Mantra Buddy couldn't answer right now. Please try again."})


if __name__ == "__main__":
    if PROVIDER == "gemini":
        print("Gemini API key loaded." if GEMINI_KEY else "Warning: GEMINI_API_KEY is not set. Add it to .env (see .env.example).")
        model = GEMINI_MODEL
    else:
        print("API key loaded." if os.environ.get("ANTHROPIC_API_KEY") else "Warning: no API key is set. Add ANTHROPIC_API_KEY or GEMINI_API_KEY to .env (see .env.example).")
        model = MODEL
    print(f"Kidzmantra running at http://{HOST}:{PORT}  ({PROVIDER}, model {model})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
