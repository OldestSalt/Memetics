import pika
import json
from dotenv import load_dotenv
import os
import logging
from PIL import Image
import boto3
import io
from vllm import LLM


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EMBEDDER")

load_dotenv()

WEAVIATE_PORT = os.getenv("WEAVIATE_PORT")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT")
DEV = bool(os.getenv("DEV"))

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost' if DEV else 'rabbitmq', port=RABBITMQ_PORT)
)
channel = connection.channel()
channel.exchange_declare(exchange="images", exchange_type="fanout")
channel.queue_declare(queue="embeddings", durable=True, exclusive=True)
channel.queue_bind(exchange="images", queue="embeddings")

boto_client = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000" if DEV else "http://minio:9000",
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
)
model = LLM(model="Qwen/Qwen3-VL-Embedding-2B", runner="pooling")

def handle_message(ch, method, properties, body):
    img_dict = json.loads(body.decode("utf-8"))
    response = boto_client.get_object(bucket_name=img_dict["bucket"], object_name=img_dict["file_name"])
    img_bytes = io.BytesIO(response["Body"].read())
    img = Image.open(img_bytes)
    img.load()

    embedding = model.embed({
        "prompt": "<|vision_start|><|image_pad|><|vision_end|>",
        "multi_modal_data": {
            "image": img
        }
    }).outputs.embedding

    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    logger.info("Starting up the queue...")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="embeddings", on_message_callback=handle_message)
    logger.info("Listening for messages...")
    channel.start_consuming()

if __name__ == '__main__':
    main()