import json
from dotenv import load_dotenv
import os
import logging
from PIL import Image
import io
from fastapi import FastAPI
from contextlib import asynccontextmanager
from vllm import VLLM

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EMBEDDER")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting up...")
        app.state.model = VLLM(model)
        logger.info("Embedder started up successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start up the gateway: {str(e)}")
        yield
    finally:
        logger.info("Shutting down...")
        await app.state.lumi_client.aclose()
        await app.state.db_manager_client.aclose()
        await app.state.data_manager_client.aclose()
        await app.state.user_manager_client.aclose()
        logger.info("Gateway shut down successfully")

app = FastAPI(
    title="Lumi",
    description="QA-assistant API",
    version="1.0.0",
    lifespan=lifespan
)

load_dotenv()



def main():


if __name__ == '__main__':
    main()