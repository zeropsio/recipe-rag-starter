import asyncio
import asyncpg
import nats
import json
import boto3
import httpx
import os
import logging
import resource
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize services
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv("AWS_ENDPOINT"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    use_ssl=True,
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

# Initialize model lazily to save memory
model = None

def get_model():
    global model
    if model is None:
        logger.info("Loading sentence transformer model...")
        try:
            memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_before = memory_kb / 1024 if memory_kb > 100000 else memory_kb / (1024 * 1024)
            logger.info(f"Memory before model loading: {memory_before:.2f}MB")
        except:
            logger.info("Memory tracking not available")
            memory_before = 0
        
        model = SentenceTransformer('all-MiniLM-L6-v2')  # Small, fast model
        
        try:
            memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_after = memory_kb / 1024 if memory_kb > 100000 else memory_kb / (1024 * 1024)
            logger.info(f"Memory after model loading: {memory_after:.2f}MB (delta: {memory_after - memory_before:.2f}MB)")
        except:
            logger.info("Model loaded successfully")
    return model

async def process_document(msg):
    data = json.loads(msg.data.decode())
    doc_id = data['id']

    print(f"Processing document {doc_id}")

    # Connect to PostgreSQL
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    try:
        # Download from S3
        obj = s3.get_object(
            Bucket=os.getenv("AWS_BUCKET"),
            Key=f"documents/{doc_id}.pdf"
        )
        content = obj['Body'].read()

        # Extract text (simplified - just use first 500 chars for demo)
        text = content.decode('utf-8', errors='ignore')[:500]

        # Create embedding
        model = get_model()
        embedding = model.encode(text).tolist()

        # Store in Qdrant
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{os.getenv('QDRANT_URL')}/collections/documents/points",
                headers={
                    "api-key": os.getenv("QDRANT_API_KEY")
                },
                json={
                    "points": [{
                        "id": doc_id,
                        "vector": embedding,
                        "payload": {
                            "text": text,
                            "filename": data['filename'],
                            "doc_id": doc_id
                        }
                    }]
                }
            )

        # Update PostgreSQL
        await conn.execute("""
            UPDATE documents
            SET processed = true, text_preview = $1
            WHERE id = $2
        """, text[:200], doc_id)

        print(f"Processed document {doc_id}")

    finally:
        await conn.close()

async def main():
    # Log startup memory
    try:
        memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_mb = memory_kb / 1024 if memory_kb > 100000 else memory_kb / (1024 * 1024)
        logger.info(f"Processor startup memory usage: {memory_mb:.2f}MB")
    except Exception as e:
        logger.info(f"Could not get startup memory usage: {e}")
    
    # Preload the model during startup
    logger.info("Preloading sentence transformer model...")
    get_model()
    logger.info("Model preloaded successfully")
    
    logger.info("Connecting to NATS...")
    nc = await nats.connect(
        os.getenv("NATS_URL"),
        user=os.getenv("NATS_USER"),
        password=os.getenv("NATS_PASSWORD")
    )
    logger.info("NATS connection successful")

    # Subscribe to processing queue
    sub = await nc.subscribe("document.process", cb=process_document)
    logger.info("Subscribed to document.process queue")

    logger.info("Processor started, waiting for documents...")

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())