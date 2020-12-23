import dotenv
import os
import logging

import voice_activity
import voice_activity.modules

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

def main():
    dotenv.load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if token is None:
        raise RuntimeError("BOT_TOKEN env variable has to be set")
    LOGGER.info("Running bot...")
    bot = voice_activity.bot.create_bot()
    bot.run(token)

if __name__ == '__main__':
    main()
