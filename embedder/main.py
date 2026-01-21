import pika
import json
from dotenv import load_dotenv
import os
import logging
from PIL import Image
import boto3
import io
from openai import OpenAI
import weaviate
import base64

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EMBEDDER")

load_dotenv()

WEAVIATE_PORT = int(os.getenv("WEAVIATE_PORT"))
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT"))
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
VLLM_PORT = int(os.getenv("VLLM_PORT"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
DEV = bool(int(os.getenv("DEV")))

logger.info("Starting up boto client")
boto_client = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000" if DEV else "http://minio:9000",
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
)
logger.info("Done")

if DEV:
    logger.info("Starting with dev mode")
else:
    logger.info("Starting with production mode")

logger.info("Starting up Weaviate client")
weaviate_client = weaviate.connect_to_local(
    host="localhost" if DEV else "weaviate",
    port=WEAVIATE_PORT,
    grpc_port=WEAVIATE_GRPC_PORT,
)
if not weaviate_client.collections.exists(COLLECTION_NAME):
    logger.info(f"Collection does not exist yet, creating '{COLLECTION_NAME}' collection")
    weaviate_client.collections.create(
        COLLECTION_NAME,
        vector_config=weaviate.classes.config.Configure.Vectors.self_provided()
    )
collection = weaviate_client.collections.use(COLLECTION_NAME)
logger.info("Done")

logger.info("Preparing the embedding model")
model_client = OpenAI(
    api_key="",
    base_url=f"http://vllm:{VLLM_PORT}/v1"
)
logger.info("Done")

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
channel.queue_declare(queue="embeddings", durable=True, exclusive=True)
channel.queue_bind(exchange="images", queue="embeddings")

def handle_message(ch, method, properties, body):
    logger.info(f"Received message")
    img_dict = json.loads(body.decode("utf-8"))
    response = boto_client.get_object(Bucket=img_dict["bucket"], Key=img_dict["file_name"])
    b64 = base64.b64encode(response["Body"].read()).decode()

    logger.info("Embedding")
    embedding = model_client.embeddings.create(
        model="Qwen/Qwen3-VL-Embedding-2B",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "<|vision_start|><|image_pad|><|vision_end|>"},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
            ]
        }]
    ).data[0].embedding

    logger.info("Inserting to database")
    collection.data.insert(
        properties={
            "bucket": img_dict["bucket"],
            "file_name": img_dict["file_name"],
        },
        vector=embedding,
    )

    ch.basic_ack(delivery_tag=method.delivery_tag)
    logger.info("Done. Acknowledged has been sent")

def main():
    logger.info("Starting up the queue...")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="embeddings", on_message_callback=handle_message)
    logger.info("Ready. Listening for messages...")
    channel.start_consuming()

if __name__ == '__main__':
    main()