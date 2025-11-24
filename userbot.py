import re
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from aiohttp import web

# ENV variables for secure config (set on Render)
API_ID = int(os.getenv('API_ID', ''))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')  # Generate this securely, not your password!

TERABOX_PATTERN = r'(https?://(?:www\.)?terabox\.com/[A-Za-z0-9/?=_\-]+)'
LINK_CONVERT_BOT = 'LinkConvertTerabot'

# Initialize Telegram client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True, from_users=None, func=lambda e: e.is_private))
async def handle_private_dm(event):
    # Only process messages not from yourself
    if event.sender_id == (await client.get_me()).id:
        return
    # Search for Terabox links
    matches = re.findall(TERABOX_PATTERN, event.raw_text)
    if not matches:
        return
    user_id = event.sender_id
    for link in matches:
        # Forward to @LinkConvertTerabot
        sent_msg = await client.send_message(LINK_CONVERT_BOT, link)
        # Wait for bot response (timeout 60s)
        try:
            response = await client.wait_for(events.NewMessage(from_users=LINK_CONVERT_BOT), timeout=60)
            await client.send_message(user_id, response.text)
        except asyncio.TimeoutError:
            await client.send_message(user_id, "Timed out waiting for link conversion.")
        await asyncio.sleep(1)  # Prevent flooding

# Minimal web server for Render health check
async def handle(request):
    return web.Response(text="OK!")

def main():
    app = web.Application()
    app.router.add_get('/', handle)
    loop = asyncio.get_event_loop()
    loop.create_task(client.start())
    web.run_app(app, port=int(os.environ.get('PORT', 8080)))

if __name__ == "__main__":
    main()
