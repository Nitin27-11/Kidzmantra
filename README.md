# Kidzmantra

An AI learning buddy for kids from Nursery to Class 8 (Nursery, LKG, UKG, Class 1 to 8). The website is split into classes, then subjects, then chapters. On every page, kids can ask "Mantra Buddy" (Claude or Gemini) anything. It can answer about the chapter they're on or about anything else in the world, and it searches the web when it needs fresh facts.

## Run it

1. Copy `.env.example` to `.env` and paste either an Anthropic API key (from https://platform.claude.com/settings/keys) or a Gemini API key (from https://aistudio.google.com/apikey).
2. Start the server:
   ```sh
   ./run.sh
   ```
3. Open http://127.0.0.1:8000

## Files

| File | What it does |
|---|---|
| `public/index.html` | The whole website: classes, subjects, chapters and the chat box |
| `server.py` | Serves the site and answers questions at `POST /api/ask` |
| `.env` | Your API key and optional settings (never share or commit this) |

## Settings (in `.env`)

| Setting | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Claude key (this or the Gemini key is required) |
| `GEMINI_API_KEY` | none | Gemini key |
| `AI_PROVIDER` | auto | `claude` or `gemini`; auto uses Gemini only when there is no Claude key |
| `GEMINI_MODEL` | `gemini-flash-latest` | Gemini model used for answers |
| `GEMINI_FALLBACK_MODEL` | `gemini-flash-lite-latest` | Lighter Gemini model used when the main one is busy |
| `GEMINI_TTS_MODEL` | `gemini-3.8-flash-tts` | Gemini model for the tutor voice |
| `GEMINI_VOICE` | `Sulafat` | Which Gemini voice reads answers (a warm female voice) |
| `PORT` | `8000` | Port to run on |
| `HOST` | `127.0.0.1` | Use `0.0.0.0` when hosting on a server |
| `RATE_LIMIT` | `30` | Questions allowed per visitor every 10 minutes |
| `KIDZMANTRA_MODEL` | `claude-opus-5-5` | Claude model used for answers |
| `KIDZMANTRA_EFFORT` | `medium` | How hard it thinks: `low`, `medium` or `high` |

## How answers are kept kid-safe

The system prompt in `server.py` tells Claude to:

- answer at the child's class level
- keep content age-appropriate
- never ask for personal details
- point a child who seems unsafe to a trusted adult or Childline (1098)

With Claude, web search is limited to 3 searches per question. With a free Gemini key, Google Search isn't included, so Gemini answers without it. If a question is declined, the child sees a gentle "let's try another question" message.

## Voice

Every chat box has voice controls. Answers are read by a warm, natural tutor voice made by Gemini (`POST /api/speak`, needs the Gemini key). If that voice is busy or not set up, the browser's own voice is used instead.

- **Answer & listen in:** English or हिंदी. Mantra Buddy answers in that language and reads it aloud.
- **🔊 English / 🔊 हिंदी** under each answer: listen in either language. Picking the other language translates the answer first (`POST /api/translate`).
- **Voice speed:** 1x (a little slower than normal, for children), 1.5x or 2x.
- **Read answers aloud:** turn automatic reading on or off.
- **🎤 Speak / Ask by voice in:** ask a question out loud in English or Hindi. Works in Chrome, Edge and Safari, not Firefox.
- While an answer is read, the current paragraph glows and each word is highlighted as it is spoken.
