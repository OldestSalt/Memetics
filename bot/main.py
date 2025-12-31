import aiohttp
from telegram.ext import MessageHandler, Application, ContextTypes, filters
from telegram import Update
from dotenv import load_dotenv
import logging
import os
import aioboto3
from minio import Minio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv("../.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEV = os.getenv("DEV")

minio_client = Minio(
    endpoint="http://localhost:9000" if DEV else "http://minio:9000",
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD")
)

async def upload_file(path):
    session = aioboto3.Session()
    async with session.Client(
        "s3",
        endpoint_url="http://localhost:9000" if DEV else "http://minio:9000",
        aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
    ) as client:
        await client.upload_file(path, "memes", path)

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.effective_message.photo if update.effective_message.photo else None
    if photo:
        photo_file = await photo[-1].get_file()
        img = await photo_file.download_to_drive("./temp/")
        await upload_file(img)
        # add to rabbitmq queue


def main():
    if BOT_TOKEN is None:
        raise ValueError("Bot token is not defined")
    if not os.path.exists("./temp"):
        os.mkdir("./temp")
    if not minio_client.bucket_exists("memes"):
        minio_client.make_bucket("memes")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(~filters.FORWARDED, log_message))

    application.run_polling(allowed_updates=Update.CHANNEL_POST)

if __name__ == '__main__':
    main()