# Gemini Search Chat

A minimal search bar with a chat-like experience, backed by the Google
Gemini API with tool (function) calling. Includes two example tools —
`calculate` and `get_current_time` — that Gemini can invoke on its own
when a query calls for them.

## Setup

```bash
cd gemini-search
npm install
cp .env.example .env   # add your GEMINI_API_KEY
npm start
```

Then open <http://localhost:3000>.

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## How it works

- `tools.js` declares the available tools (JSON schema Gemini uses to
  decide when to call them) and implements them locally.
- `server.js` exposes `POST /api/chat`. It starts/continues a Gemini chat
  with those tools attached, executes any function calls the model
  requests, feeds the results back, and returns the final text reply
  (plus a log of any tool calls made).
- `public/` is a static frontend: a search bar that renders the
  conversation as chat bubbles, including a small trace of any tool
  calls Gemini made along the way.

## Adding a new tool

1. Add a function declaration (name, description, parameters) to
   `declarations` in `tools.js`.
2. Implement the matching function and register it in `implementations`.

Gemini will automatically start calling it when relevant — no changes to
`server.js` are needed.
