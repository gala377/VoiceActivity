import dotenv
import os

from voice_activity import bot

def main():
    dotenv.load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if token is None:
        raise RuntimeError("BOT_TOKEN env variable has to be set")
    print("Running bot...")
    bot.run_client(token)

if __name__ == '__main__':
    main()
