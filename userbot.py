import re
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from aiohttp import web

# Environment variables (set these in Render dashboard)
API_ID = int(os.getenv('API_ID', ''))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')

# Updated regex pattern with non-capturing groups to avoid tuple results from findall
TERABOX_PATTERN = r'(https?://[^\s]*(?:teraboxshare\.com|1024tera\.com)[^\s]*)'

LINK_CONVERT_BOT = 'LinkConvertTerabot'

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True, from_users=None, func=lambda e: e.is_private))
async def handle_private_dm(event):
    # Ignore messages from self
    if event.sender_id == (await client.get_me()).id:
        return

    matches = re.findall(TERABOX_PATTERN, event.raw_text)
    if not matches:
        return

    user_id = event.sender_id
    for link in matches:
        # Make sure link is a string (it should be with current regex)
        if not isinstance(link, str):
            link = ''.join(link)
        try:
            # Send the Terabox link to the converter bot
            sent_msg = await client.send_message(LINK_CONVERT_BOT, link)
            # Wait for response with a timeout of 60 seconds
            response = await client.wait_for(events.NewMessage(from_users=LINK_CONVERT_BOT), timeout=60)
            # Send converted link back to original user
            await client.send_message(user_id, response.text)
        except asyncio.TimeoutError:
            await client.send_message(user_id, "Timed out waiting for link conversion.")
        await asyncio.sleep(1)  # To prevent flooding

# Simple webserver for Render health check
async def handle(request):
    return web.Response(text="OK!")

async def main():
    await client.start()
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()

    print("Userbot running and webserver started...")
    # Keep the service alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
