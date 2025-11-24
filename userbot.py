import re
import asyncio
import os
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from aiohttp import web

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables - set these in Render dashboard
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')

if not (API_ID and API_HASH and SESSION_STRING):
    logger.error("API_ID, API_HASH, or SESSION_STRING environment variables missing.")
    exit(1)

# Regex to match various Terabox link formats
TERABOX_PATTERN = r'(https?://[^\s]*(?:teraboxshare\.com|1024tera\.com)[^\s]*)'
LINK_CONVERT_BOT = 'LinkConvertTerabot'

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def wait_for_bot_response(client, bot_username, timeout=60):
    future = asyncio.get_event_loop().create_future()

    @client.on(events.NewMessage(from_users=bot_username))
    async def handler(event):
        if not future.done():
            future.set_result(event)

    try:
        response_event = await asyncio.wait_for(future, timeout=timeout)
        client.remove_event_handler(handler)
        return response_event
    except asyncio.TimeoutError:
        client.remove_event_handler(handler)
        raise

@client.on(events.NewMessage(incoming=True, from_users=None, func=lambda e: e.is_private))
async def handle_private_dm(event):
    logger.info(f"Incoming message from user_id={event.sender_id}: {event.raw_text}")

    # Ignore messages from self
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
            response_event = await wait_for_bot_response(client, LINK_CONVERT_BOT, timeout=60)
            logger.info(f"Received response from converter bot: {response_event.text}")
            await client.send_message(user_id, response_event.text)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response from {LINK_CONVERT_BOT}")
            await client.send_message(user_id, "Timed out waiting for link conversion.")
        await asyncio.sleep(1)

# Simple health check endpoint
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

    # Keep the service running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
