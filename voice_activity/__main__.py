import dotenv
import os
import logging

from voice_activity import bot

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

def main():
    dotenv.load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if token is None:
        raise RuntimeError("BOT_TOKEN env variable has to be set")
    LOGGER.info("Running bot...")
    bot.run_client(token)

if __name__ == '__main__':
    main()
