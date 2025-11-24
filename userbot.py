import re
import asyncio
import os
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from aiohttp import web

# Setup simple console logging for debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')

if not (API_ID and API_HASH and SESSION_STRING):
    logger.error("API_ID, API_HASH, or SESSION_STRING environment variables missing or empty.")
    exit(1)

TERABOX_PATTERN = r'(https?://[^\s]*(?:teraboxshare\.com|1024tera\.com)[^\s]*)'
LINK_CONVERT_BOT = 'LinkConvertTerabot'

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True, from_users=None, func=lambda e: e.is_private))
async def handle_private_dm(event):
    logger.info(f"Incoming message from user_id={event.sender_id}: {event.raw_text}")

    if event.sender_id == (await client.get_me()).id:
        logger.info("Message from self ignored.")
        return

    matches = re.findall(TERABOX_PATTERN, event.raw_text)
    if not matches:
        logger.info("No Terabox links found in the message.")
        return

    user_id = event.sender_id
    for link in matches:
        if not isinstance(link, str):
            link = ''.join(link)

        logger.info(f"Sending link to converter bot: {link}")
        try:
            await client.send_message(LINK_CONVERT_BOT, link)
            response = await client.wait_for(events.NewMessage(from_users=LINK_CONVERT_BOT), timeout=60)
            logger.info(f"Received response from converter bot: {response.text}")
            await client.send_message(user_id, response.text)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response from {LINK_CONVERT_BOT}")
            await client.send_message(user_id, "Timed out waiting for link conversion.")
        await asyncio.sleep(1)

async def handle(request):
    return web.Response(text="OK!")

async def main():
    await client.start()
    logger.info("Telegram client started.")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    logger.info("Web server started.")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
