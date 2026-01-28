import json
from dotenv import load_dotenv
import os
import logging
from PIL import Image
import io
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from vllm import LLM
import models
import base64

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EMBEDDER")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting up...")
        app.state.model = LLM(model="Qwen/Qwen3-VL-Embedding-2B", runner="pooling", gpu_memory_utilization=0.8, max_model_len=4096)
        logger.info("Embedder started up successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start up the embedder: {str(e)}")
        yield
    finally:
        logger.info("Shutting down...")
        logger.info("Embedder shut down successfully")

app = FastAPI(
    title="Embedder",
    description="Service for embedding multimodal data",
    version="1.0.0",
    lifespan=lifespan
)

load_dotenv()
PORT = int(os.getenv("EMBEDDER_PORT"))

@app.post("/embeddings", response_model=models.EmbeddingsResponse)
def embeddings(request: models.EmbeddingsRequest) -> models.EmbeddingsResponse:
    images = [Image.open(io.BytesIO(base64.b64decode(image))) for image in request.images]
    embedding = app.state.model.embed({
        "prompt": f"<|vision_start|>" + "<|image_pad|>" * len(images) + f"<|vision_end|>\n{request.text}",
        "multi_modal_data": {"image": [image for image in images]},
    })[0].outputs.embedding
    return models.EmbeddingsResponse(
        embedding=embedding
    )

def main():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()