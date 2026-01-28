import json
from dotenv import load_dotenv
import os
import logging
from PIL import Image
import io
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
import models
import httpx
import weaviate
from weaviate.classes.query import MetadataQuery
import aioboto3
import base64

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("API")

load_dotenv("../.env")
DEV = bool(int(os.getenv("DEV")))
PORT = int(os.getenv("API_PORT"))
EMBEDDER_PORT = int(os.getenv("EMBEDDER_PORT"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
WEAVIATE_PORT = int(os.getenv("WEAVIATE_PORT"))
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting up...")
        app.state.embedder_client = httpx.AsyncClient(
            base_url=f"http://localhost:{EMBEDDER_PORT}" if DEV else f"http://embedder:{EMBEDDER_PORT}",
            timeout=None
        )

        logger.info("Connecting to Weaviate...")
        app.state.weaviate_client = weaviate.use_async_with_local(
            host="localhost" if DEV else "weaviate",
            port=WEAVIATE_PORT,
            grpc_port=WEAVIATE_GRPC_PORT,
        )
        await app.state.weaviate_client.connect()
        if not await app.state.weaviate_client.collections.exists(COLLECTION_NAME):
            logger.info(f"Collection does not exist yet, creating '{COLLECTION_NAME}' collection")
            await app.state.weaviate_client.collections.create(
                COLLECTION_NAME,
                vector_config=weaviate.classes.config.Configure.Vectors.self_provided()
            )
        app.state.collection = app.state.weaviate_client.collections.use(COLLECTION_NAME)

        logger.info("Connecting to Minio...")
        app.state.boto_session = aioboto3.Session()

        logger.info("API started up successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start up API: {str(e)}")
        raise e
    finally:
        logger.info("Shutting down...")
        await app.state.weaviate_client.close()
        await app.state.embedder_client.aclose()
        logger.info("API shut down successfully")

app = FastAPI(
    title="Memetics API",
    description="Multifunctional API for Memetics (c)",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/search", response_model=models.SearchResponse)
async def search(request: models.SearchRequest) -> models.SearchResponse:
    embedding = (await app.state.embedder_client.post(
        "/embeddings",
        json={
            "text": request.text,
            "images": request.images
        }
    )).json()["embedding"]

    results = await app.state.collection.query.near_vector(
        near_vector=embedding,
        limit=request.k,
        return_metadata=MetadataQuery(distance=True),
    )

    async with app.state.boto_session.client(
        "s3",
        endpoint_url="http://localhost:9000" if DEV else "http://minio:9000",
        aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
    ) as client:
        return models.SearchResponse(
            results=[
                models.SearchResult(
                    images=[
                        base64.b64encode(await ((await client.get_object(Bucket=image["bucket"], Key=image["file_name"]))["Body"].read())).decode("utf-8")
                        for image in result.properties['images']
                    ],
                    text=result.properties['text'],
                    score=result.metadata.distance
                )
                for result in results.objects
            ]
        )

def main():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()