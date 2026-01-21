import pika
import json
from dotenv import load_dotenv
from typing import Any
import os
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    create_engine
)
from models import Images, Base
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DB_MANAGER")

load_dotenv()

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
        )
    )
)
channel = connection.channel()
channel.exchange_declare(exchange="images", exchange_type="fanout")
channel.queue_declare(queue="postgres", durable=True, exclusive=True)
channel.queue_bind(exchange="images", queue="postgres")

class DatabaseManager:
    def __init__(self, db_url: str):
        logger.info("Starting engine...")
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(
            self.engine, expire_on_commit=False
        )
        logger.info("Creating tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Done")

    def add_image(self, image_dict: dict[str, Any]) -> None:
        with self.Session() as session:
            image = Images(
                **image_dict,
                uploaded_at=datetime.now()
            )
            session.add(image)
            logger.info("Adding image to database...")
            session.commit()
            logger.info("Done")

db_manager = DatabaseManager(os.getenv("POSTGRES_URL"))

def handle_message(ch, method, properties, body):
    logger.info(f"Received message")
    img_dict = json.loads(body.decode("utf-8"))
    db_manager.add_image(img_dict)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    logger.info("Done. Acknowledged has been sent")

def main():
    logger.info("Starting up the queue...")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="postgres", on_message_callback=handle_message)
    logger.info("Listening for messages...")
    channel.start_consuming()

if __name__ == '__main__':
    main()