# WhatsApp support bot

Customer messages you on WhatsApp -> bot sends a welcome with your logo and asks
how it can help -> answers from `knowledge_base.md` in simple language -> if the
answer isn't there, it uses public web search.

## Setup
1. Create a Meta app with the **WhatsApp** product (developers.facebook.com); note the
   temporary/permanent token and the Phone Number ID.
2. `cp .env.example .env`, fill it in (set `LOGO_URL` to a public https image).
3. Edit `knowledge_base.md` with your business details (FAQs, prices, hours, policies).
4. Run:
   ```
   pip install -r requirements.txt
   set -a; . ./.env; set +a
   gunicorn -b 0.0.0.0:8000 app:app
   ```
5. Expose it over https (e.g. `ngrok http 8000`) and in Meta > WhatsApp > Configuration set
   Callback URL `https://<host>/webhook`, Verify token = `VERIFY_TOKEN`, and subscribe to **messages**.

## Notes
- Sessions are kept in memory (greeting repeats after 24h of silence; restarts reset it).
  Swap `sessions` for Redis/DB for multi-instance deployments.
- Web search uses Claude's built-in web search tool; enable it for your API org in the Anthropic Console.
- Only text messages are handled; other types get a polite nudge.
