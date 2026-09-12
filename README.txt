NEXORA AI — Groq + Gemini Quota Protection

Run:
  python server.py

Open:
  http://127.0.0.1:8787

Gemini quota behavior:
- Gemini 429 / RESOURCE_EXHAUSTED is detected server-side.
- NEXORA shows a clean "GEMINI // LIMIT REACHED" card.
- The card includes an UPGRADE SUBSCRIPTION button to Google AI Studio Billing.
- API keys remain server-side in .env and are NOT included in this package.

Example .env:
  GEMINI_API_KEY=YOUR_GEMINI_API_KEY
  GEMINI_MODEL=gemini-3.6-flash
  GROQ_API_KEY=YOUR_GROQ_API_KEY
  GROQ_MODEL=openai/gpt-oss-20b
  NEXORA_PORT=8787

Never commit .env to GitHub.


INSTAGRAM DM INTEGRATION
------------------------
NEXORA now includes an Instagram DM HUD and a secure Python webhook receiver.

What it does:
- Shows received Instagram text DMs in the NEXORA HUD.
- Stores the latest 100 received messages locally in instagram_messages.json.
- Lets NEXORA answer questions such as "What are my new Instagram DMs?"
  by injecting the currently stored DM context into the AI request.
- Keeps Instagram credentials server-side in .env.
- Provides /api/instagram/status for the HUD.
- Provides /webhooks/instagram for Meta webhook verification and incoming events.

IMPORTANT:
A normal website cannot read Instagram private DMs by itself. You must connect
an eligible Instagram/Meta account through Meta's official messaging products,
configure the webhook, and provide the required server-side credentials.

Add to .env:
  INSTAGRAM_ACCESS_TOKEN=YOUR_TOKEN
  INSTAGRAM_ACCOUNT_ID=YOUR_INSTAGRAM_ACCOUNT_ID
  INSTAGRAM_VERIFY_TOKEN=MAKE_A_RANDOM_PRIVATE_VERIFY_TOKEN

The webhook URL must be a PUBLIC HTTPS URL. http://127.0.0.1:8787 cannot receive
Meta webhooks directly from the internet. Use a secure HTTPS tunnel or deploy
the Python backend to a public HTTPS server.

Webhook endpoint:
  https://YOUR-PUBLIC-HOST/webhooks/instagram

Meta webhook verification:
- Use the exact INSTAGRAM_VERIFY_TOKEN value in the Meta webhook configuration.
- Meta's challenge is verified server-side; the token is never sent to the browser.

Local test:
  POST /api/instagram/test with JSON:
  {"sender":"Demo User","text":"Hello NEXORA"}

After a test message is stored, ask:
  "What are my Instagram DMs?"
and NEXORA will read the stored message context.

No Instagram password is required or supported. Do not paste account passwords
into NEXORA.
