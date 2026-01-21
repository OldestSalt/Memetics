from telegram.ext import MessageHandler, Application, ContextTypes, filters
from telegram import Update
from dotenv import load_dotenv
import logging
import os
import aioboto3
from minio import Minio
import pika
import json
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("BOT")

load_dotenv("../.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
IMG_BUCKET_NAME = os.getenv("IMG_BUCKET_NAME")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
DEV = bool(int(os.getenv("DEV")))

if DEV:
    logger.info("Starting with dev mode")
else:
    logger.info("Starting with production mode")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost" if DEV else "rabbitmq",
        port=RABBITMQ_PORT,
        credentials=pika.PlainCredentials(
            username=os.getenv("RABBITMQ_USER"),
            password=os.getenv("RABBITMQ_PASSWORD")
        ),
        heartbeat=0
    )
)
channel = connection.channel()
channel.exchange_declare(exchange="images", exchange_type="fanout")

minio_client = Minio(
    endpoint="localhost:9000" if DEV else "minio:9000",
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    secure=False
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
    try:
        if photo:
            logger.info("Image intercepted")
            photo_file = await photo[-1].get_file()
            img = await photo_file.download_to_drive()
            img = img.rename(str(uuid4()) + ".jpg")
            await upload_file(str(img))
            img_name = os.path.split(img)[1]
            img.unlink()
            img_json = json.dumps({"file_name": img_name, "bucket": IMG_BUCKET_NAME})
            channel.basic_publish(exchange="images", routing_key="", body=img_json.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error while processing image: {e}")
        raise e


def main():
    try:
        logger.info("Starting up")
        if BOT_TOKEN is None:
            raise ValueError("Bot token is not defined")
        # if not os.path.exists("./temp"):
        #     os.mkdir("./temp")
        if not minio_client.bucket_exists(IMG_BUCKET_NAME):
            minio_client.make_bucket(IMG_BUCKET_NAME)

        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .connect_timeout(20)
            .read_timeout(20)
            .write_timeout(20)
            .pool_timeout(10)
            .build()
        )
        application.add_handler(MessageHandler(~filters.FORWARDED, log_message))
        logger.info("Bot application started, listening for telegram messages")

        application.run_polling(allowed_updates=Update.CHANNEL_POST)
    except Exception as e:
        logger.error(e)
        connection.close()
        raise e

if __name__ == '__main__':
    main()