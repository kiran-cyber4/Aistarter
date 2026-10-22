"""Simple WhatsApp support bot: greets with logo, answers from a knowledge base,
falls back to public web search when the knowledge base has no answer."""
import hashlib
import hmac
import logging
import os
import time
from pathlib import Path

import anthropic
import requests
from flask import Flask, abort, request

log = logging.getLogger("bot")
logging.basicConfig(level=logging.INFO)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
APP_SECRET = os.getenv("APP_SECRET", "")
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "our business")
LOGO_URL = os.getenv("LOGO_URL", "")
KB = Path(__file__).with_name("knowledge_base.md").read_text()

SESSION_TTL = 24 * 3600  # greet again after a day of silence
HISTORY_TURNS = 6
NOT_FOUND = "NOT_IN_KB"

STYLE = (
    "You are a friendly WhatsApp assistant for {name}. Reply in short, simple, "
    "plain language (a few sentences, no jargon, no markdown headings). "
    "Reply in the customer's language. Use at most one emoji."
)
KB_SYSTEM = (
    STYLE
    + "\n\nAnswer ONLY using the knowledge base below. If it does not contain "
    f"the answer, reply with exactly {NOT_FOUND} and nothing else. Greetings and "
    "thanks do not need the knowledge base - answer them normally.\n\n"
    "KNOWLEDGE BASE:\n{kb}"
)
WEB_SYSTEM = (
    STYLE
    + "\n\nThe business knowledge base had no answer, so use web search to answer "
    "helpfully and accurately. If the question is about {name}'s own prices, "
    "bookings or policies, do not guess: say you will ask the team and suggest "
    "contacting them. Mention briefly that the answer comes from public sources."
)

client = anthropic.Anthropic()
app = Flask(__name__)
sessions: dict[str, dict] = {}  # phone -> {"seen": ts, "history": [...]}


# ---------- WhatsApp helpers ----------
def _send(payload: dict) -> None:
    r = requests.post(
        f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        json={"messaging_product": "whatsapp", **payload},
        timeout=15,
    )
    if not r.ok:
        log.error("WhatsApp send failed: %s %s", r.status_code, r.text)


def send_text(to: str, text: str) -> None:
    _send({"to": to, "type": "text", "text": {"body": text[:4000]}})


def send_welcome(to: str) -> None:
    caption = (
        f"👋 Welcome to *{BUSINESS_NAME}*!\n"
        "We're happy to have you here and glad to help.\n\n"
        "How can we help you today?"
    )
    if LOGO_URL:
        _send({"to": to, "type": "image", "image": {"link": LOGO_URL, "caption": caption}})
    else:
        send_text(to, caption)


def mark_read(msg_id: str) -> None:
    _send({"status": "read", "message_id": msg_id})


# ---------- Answering ----------
def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def answer(history: list[dict]) -> str:
    resp = client.messages.create(
        model=MODEL, max_tokens=500,
        system=KB_SYSTEM.format(name=BUSINESS_NAME, kb=KB), messages=history,
    )
    out = _text(resp)
    if NOT_FOUND not in out:
        return out
    log.info("KB miss, using web search")
    resp = client.messages.create(
        model=MODEL, max_tokens=800,
        system=WEB_SYSTEM.format(name=BUSINESS_NAME), messages=history,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
    )
    return _text(resp) or "Sorry, I couldn't find that. Our team will get back to you soon."


def handle_message(phone: str, text: str) -> None:
    now = time.time()
    s = sessions.get(phone)
    if not s or now - s["seen"] > SESSION_TTL:
        s = sessions[phone] = {"seen": now, "history": []}
        send_welcome(phone)
        if len(text.strip()) < 15 and text.strip().lower().strip("!. ") in {
            "hi", "hello", "hey", "hii", "hola", "namaste", "good morning",
            "good afternoon", "good evening", "start", "menu"}:
            return  # pure greeting: welcome already asks how we can help
    s["seen"] = now
    s["history"].append({"role": "user", "content": text})
    del s["history"][:-HISTORY_TURNS]
    while s["history"] and s["history"][0]["role"] != "user":
        del s["history"][0]
    try:
        reply = answer(s["history"])
    except Exception:
        log.exception("answer failed")
        reply = "Sorry, something went wrong on our side. Please try again in a moment."
        s["history"].pop()
        send_text(phone, reply)
        return
    s["history"].append({"role": "assistant", "content": reply})
    send_text(phone, reply)


# ---------- Webhook ----------
@app.get("/webhook")
def verify():
    if VERIFY_TOKEN and request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge", ""), 200
    abort(403)


@app.post("/webhook")
def receive():
    if APP_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        want = "sha256=" + hmac.new(APP_SECRET.encode(), request.get_data(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, want):
            abort(403)
    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []):
                phone = m["from"]
                mark_read(m["id"])
                if m.get("type") == "text":
                    handle_message(phone, m["text"]["body"])
                else:
                    send_text(phone, "Thanks! I can only read text messages right now. Please type your question.")
    return "ok", 200  # always 200 so Meta doesn't retry


@app.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 8000)))
