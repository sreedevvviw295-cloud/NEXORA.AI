"""
NEXORA Phase 2 local backend.
Pure Python standard library — no Node.js, npm, or Python packages required.

Run:
    python server.py

Then open:
    http://127.0.0.1:8787

API keys are read from environment variables or a local .env file.
Never put keys in index.html or script.js.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
import os

PORT = int(os.environ.get("PORT", 8787))

server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
server.serve_forever()
def load_env():
    env = ROOT / ".env"
    if not env.exists():
        return
    for raw in env.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)

load_env()

INSTAGRAM_STORE = ROOT / "instagram_messages.json"
INSTAGRAM_MAX_MESSAGES = 100

def instagram_configured():
    return bool(os.getenv("INSTAGRAM_ACCESS_TOKEN") and os.getenv("INSTAGRAM_ACCOUNT_ID"))

def instagram_webhook_ready():
    return bool(os.getenv("INSTAGRAM_VERIFY_TOKEN"))

def load_instagram_messages():
    if not INSTAGRAM_STORE.exists():
        return []
    try:
        data=json.loads(INSTAGRAM_STORE.read_text(encoding="utf-8"))
        return data if isinstance(data,list) else []
    except Exception:
        return []

def save_instagram_messages(items):
    INSTAGRAM_STORE.write_text(json.dumps(items[-INSTAGRAM_MAX_MESSAGES:],ensure_ascii=False,indent=2),encoding="utf-8")

def format_dm_time(ts):
    try:
        value=float(ts)
        return time.strftime("%d %b %H:%M", time.localtime(value))
    except Exception:
        return "LIVE"

def extract_instagram_messages(payload):
    """Accept common Meta webhook shapes without requiring any client-side secret."""
    found=[]
    entries=payload.get("entry",[]) if isinstance(payload,dict) else []
    if isinstance(entries,dict):
        entries=[entries]
    for entry in entries:
        messaging=entry.get("messaging",[]) if isinstance(entry,dict) else []
        if isinstance(messaging,dict):
            messaging=[messaging]
        for event in messaging:
            if not isinstance(event,dict):
                continue
            message=event.get("message") or {}
            text=message.get("text")
            sender=event.get("sender") or {}
            recipient=event.get("recipient") or {}
            if text:
                ts=event.get("timestamp") or int(time.time()*1000)
                # Meta timestamps are commonly milliseconds.
                sec=float(ts)/1000 if float(ts)>10_000_000_000 else float(ts)
                found.append({
                    "id":message.get("mid") or f"ig-{int(sec*1000)}-{len(found)}",
                    "sender_id":str(sender.get("id","")),
                    "sender_name":str(sender.get("username") or sender.get("name") or sender.get("id") or "INSTAGRAM USER"),
                    "recipient_id":str(recipient.get("id","")),
                    "text":str(text),
                    "timestamp":sec,
                    "time_display":format_dm_time(sec),
                    "unread":True
                })
    return found

def instagram_context():
    items=load_instagram_messages()
    if not items:
        return ""
    lines=[]
    for m in items[-20:]:
        lines.append(f'- {m.get("sender_name","INSTAGRAM USER")} [{m.get("time_display","LIVE")}]: {m.get("text","")}')
    return (
        "\n\nPRIVATE INSTAGRAM DM CONTEXT (only use this when the user asks about their Instagram DMs/messages):\n"
        + "\n".join(lines)
        + "\nTreat these as the messages currently received by the user's connected Instagram account. "
          "Do not invent messages, send messages, or claim access to older DMs that are not in this context."
    )

SYSTEM_PROMPT = """You are NEXORA, a futuristic multi-AI assistant.
Be helpful, clear, accurate and practical. You can solve problems, explain concepts,
write and debug code, help design websites, brainstorm ideas, and assist with tasks.
Do not claim to have performed actions you did not perform. When code is requested,
provide production-minded code and explain important setup steps briefly."""

def http_json(url, headers, payload, timeout=90):
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={**headers, "Content-Type":"application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
        except Exception:
            detail = body
        raise RuntimeError(f"HTTP {e.code}: {detail}")
    except URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")

def openai_call(message):
    key=os.getenv("OPENAI_API_KEY")
    if not key: raise RuntimeError("OPENAI_API_KEY is not configured")
    model=os.getenv("OPENAI_MODEL","gpt-5.4")
    payload={"model":model,"instructions":SYSTEM_PROMPT,"input":message}
    data=http_json("https://api.openai.com/v1/responses",
                   {"Authorization":f"Bearer {key}"},payload)
    text=data.get("output_text")
    if text: return text
    # Defensive extraction for response objects that omit the convenience field.
    chunks=[]
    for item in data.get("output",[]):
        for content in item.get("content",[]):
            if content.get("type")=="output_text":
                chunks.append(content.get("text",""))
    if chunks: return "".join(chunks)
    raise RuntimeError("OpenAI returned no text")

def gemini_call(message):
    key=os.getenv("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY is not configured")
    model=os.getenv("GEMINI_MODEL","gemini-3.6-flash")
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload={"system_instruction":{"parts":[{"text":SYSTEM_PROMPT}]},
             "contents":[{"role":"user","parts":[{"text":message}]}]}
    try:
        data=http_json(url,{"x-goog-api-key":key},payload)
    except RuntimeError as e:
        raw=str(e)
        if raw.startswith("HTTP 429") or "RESOURCE_EXHAUSTED" in raw or "quota" in raw.lower():
            raise GeminiQuotaError("Gemini API limit reached. Wait for the quota to reset or upgrade your Gemini API billing plan.")
        raise
    parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
    text="".join(p.get("text","") for p in parts)
    if text: return text
    raise RuntimeError("Gemini returned no text")

def groq_call(message):
    key=os.getenv("GROQ_API_KEY")
    if not key: raise RuntimeError("GROQ_API_KEY is not configured")
    model=os.getenv("GROQ_MODEL","openai/gpt-oss-20b")
    payload={"model":model,"messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":message}],"stream":False,"temperature":0.7,"max_completion_tokens":2048,"include_reasoning":False}
    data=http_json("https://api.groq.com/openai/v1/chat/completions",
                   {"Authorization":f"Bearer {key}"},payload)
    choices=data.get("choices",[])
    if choices:
        text=choices[0].get("message",{}).get("content","")
        if text: return text
    raise RuntimeError("Groq returned no text")

def claude_call(message):
    key=os.getenv("ANTHROPIC_API_KEY")
    if not key: raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    model=os.getenv("CLAUDE_MODEL","claude-sonnet-4-6")
    payload={"model":model,"max_tokens":4096,"system":SYSTEM_PROMPT,
             "messages":[{"role":"user","content":message}]}
    data=http_json("https://api.anthropic.com/v1/messages",
                   {"x-api-key":key,"anthropic-version":"2023-06-01"},payload)
    text="".join(x.get("text","") for x in data.get("content",[]) if x.get("type")=="text")
    if text: return text
    raise RuntimeError("Claude returned no text")

def choose_auto(message):
    q=message.lower()
    if re.search(r"\b(code|debug|javascript|typescript|python|html|css|react|api|program)\b",q):
        return "groq" if os.getenv("GROQ_API_KEY") else ("openai" if os.getenv("OPENAI_API_KEY") else ("claude" if os.getenv("ANTHROPIC_API_KEY") else "gemini"))
    if re.search(r"\b(image|photo|vision|diagram|pdf|document)\b",q):
        return "groq" if os.getenv("GROQ_API_KEY") else ("gemini" if os.getenv("GEMINI_API_KEY") else ("openai" if os.getenv("OPENAI_API_KEY") else "claude"))
    return "groq" if os.getenv("GROQ_API_KEY") else ("openai" if os.getenv("OPENAI_API_KEY") else ("gemini" if os.getenv("GEMINI_API_KEY") else ("claude" if os.getenv("ANTHROPIC_API_KEY") else None)))

CALLERS={"openai":openai_call,"gemini":gemini_call,"claude":claude_call,"groq":groq_call}
LABELS={"openai":"CHATGPT","gemini":"GEMINI","claude":"CLAUDE","groq":"GROQ"}

def chat(payload):
    message=str(payload.get("message","")).strip()
    provider=str(payload.get("provider","auto")).lower()
    if not message: raise RuntimeError("Empty message")
    if re.search(r"\b(instagram|instagram dm|dm|direct message|direct messages|ig messages|ig dm)\b", message, re.I):
        message += instagram_context()
    selected=choose_auto(message) if provider=="auto" else provider
    if selected not in CALLERS: raise RuntimeError("Unknown AI provider")
    if selected=="openai" and not os.getenv("OPENAI_API_KEY"): raise RuntimeError("OPENAI_API_KEY is not configured")
    if selected=="gemini" and not os.getenv("GEMINI_API_KEY"): raise RuntimeError("GEMINI_API_KEY is not configured")
    if selected=="claude" and not os.getenv("ANTHROPIC_API_KEY"): raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    if selected=="groq" and not os.getenv("GROQ_API_KEY"): raise RuntimeError("GROQ_API_KEY is not configured")
    return {"reply":CALLERS[selected](message),"provider":selected,"provider_label":LABELS[selected]}

class GeminiQuotaError(RuntimeError):
    def __init__(self, message, status=429):
        super().__init__(message)
        self.status = status
        self.provider = "gemini"
        self.code = "GEMINI_QUOTA_REACHED"
        self.upgrade_url = "https://aistudio.google.com/billing"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)

    def send_json(self, status, obj):
        raw=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        # Meta webhook verification handshake.
        if self.path.startswith("/webhooks/instagram"):
            from urllib.parse import urlparse, parse_qs
            q=parse_qs(urlparse(self.path).query)
            mode=q.get("hub.mode",[""])[0]
            token=q.get("hub.verify_token",[""])[0]
            challenge=q.get("hub.challenge",[""])[0]
            if mode=="subscribe" and token and token==os.getenv("INSTAGRAM_VERIFY_TOKEN",""):
                raw=challenge.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type","text/plain; charset=utf-8")
                self.send_header("Content-Length",str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            else:
                self.send_response(403); self.end_headers()
            return

        if self.path == "/api/status":
            self.send_json(200,{"openai":bool(os.getenv("OPENAI_API_KEY")),
                               "gemini":bool(os.getenv("GEMINI_API_KEY")),
                               "claude":bool(os.getenv("ANTHROPIC_API_KEY")),
                               "groq":bool(os.getenv("GROQ_API_KEY")),
                               "instagram":instagram_configured()})
            return

        if self.path == "/api/instagram/status":
            items=load_instagram_messages()
            self.send_json(200,{
                "connected":instagram_configured(),
                "webhook_ready":instagram_webhook_ready(),
                "messages":items[-20:]
            })
            return

        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/webhooks/instagram"):
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length > 200_000:
                    raise RuntimeError("Webhook request too large")
                payload=json.loads(self.rfile.read(length).decode("utf-8"))
                incoming=extract_instagram_messages(payload)
                if incoming:
                    current=load_instagram_messages()
                    existing={m.get("id") for m in current}
                    current.extend([m for m in incoming if m.get("id") not in existing])
                    save_instagram_messages(current)
                self.send_json(200,{"ok":True,"received":len(incoming)})
            except Exception as e:
                self.send_json(400,{"error":str(e),"code":"INSTAGRAM_WEBHOOK_ERROR"})
            return

        if self.path == "/api/instagram/test":
            try:
                length=int(self.headers.get("Content-Length","0"))
                payload=json.loads(self.rfile.read(length).decode("utf-8"))
                text=str(payload.get("text","")).strip()
                sender=str(payload.get("sender","TEST USER")).strip() or "TEST USER"
                if not text: raise RuntimeError("Test message is empty")
                item={"id":f"test-{int(time.time()*1000)}","sender_id":"test","sender_name":sender,
                      "recipient_id":"nexora","text":text,"timestamp":time.time(),
                      "time_display":format_dm_time(time.time()),"unread":True}
                current=load_instagram_messages(); current.append(item); save_instagram_messages(current)
                self.send_json(200,{"ok":True,"message":item})
            except Exception as e:
                self.send_json(400,{"error":str(e),"code":"INSTAGRAM_TEST_ERROR"})
            return

        if self.path != "/api/chat":
            self.send_json(404,{"error":"Not found"})
            return
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length > 100_000:
                raise RuntimeError("Request too large")
            payload=json.loads(self.rfile.read(length).decode("utf-8"))
            self.send_json(200,chat(payload))
        except GeminiQuotaError as e:
            self.send_json(429,{"error":str(e),"code":e.code,"provider":e.provider,"upgrade_url":e.upgrade_url})
        except Exception as e:
            self.send_json(500,{"error":str(e),"code":"SYSTEM_ERROR"})

if __name__=="__main__":
    print(f"NEXORA Phase 2 backend: http://{HOST}:{PORT}")
    print("Configured providers:",
          "CHATGPT" if os.getenv("OPENAI_API_KEY") else "-",
          "GEMINI" if os.getenv("GEMINI_API_KEY") else "-",
          "CLAUDE" if os.getenv("ANTHROPIC_API_KEY") else "-",
          "GROQ" if os.getenv("GROQ_API_KEY") else "-")
    print("Instagram webhook:", "READY" if instagram_webhook_ready() else "NOT CONFIGURED")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
