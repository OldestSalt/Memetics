import aiohttp
from telegram.ext import MessageHandler, Application, ContextTypes, filters
from telegram import Update
from dotenv import load_dotenv
import logging
import os
import aioboto3
from minio import Minio
import pika
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv("../.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
IMG_BUCKET_NAME = os.getenv("IMG_BUCKET_NAME")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT")
DEV = os.getenv("DEV")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost" if DEV else "rabbitmq", port=RABBITMQ_PORT)
)
channel = connection.channel()
channel.exchange_declare(exchange="images", exchange_type="fanout")

minio_client = Minio(
    endpoint="http://localhost:9000" if DEV else "http://minio:9000",
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD")
)

async def upload_file(path):
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url="http://localhost:9000" if DEV else "http://minio:9000",
        aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
    ) as client:
        await client.upload_file(path, IMG_BUCKET_NAME, path)

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.effective_message.photo if update.effective_message.photo else None
    if photo:
        photo_file = await photo[-1].get_file()
        img = await photo_file.download_to_drive("./temp/")
        await upload_file(img)
        img_name = os.path.split(img)[1]
        img.unlink()
        img_json = json.dumps({"img_name": img_name, "bucket": IMG_BUCKET_NAME})
        channel.basic_publish(exchange="images", routing_key="", body=img_json)


def main():
    try:
        if BOT_TOKEN is None:
            raise ValueError("Bot token is not defined")
        if not os.path.exists("./temp"):
            os.mkdir("./temp")
        if not minio_client.bucket_exists(IMG_BUCKET_NAME):
            minio_client.make_bucket(IMG_BUCKET_NAME)
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(MessageHandler(~filters.FORWARDED, log_message))

        application.run_polling(allowed_updates=Update.CHANNEL_POST)
    except Exception as e:
        logger.error(e)
        connection.close()
        raise e

if __name__ == '__main__':
    main()