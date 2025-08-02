from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncpg
import httpx
import nats
import boto3
import redis
import uuid
import json
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="ESG RAG Hello World")

# Enable CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service connections
s3 = None
nc = None
db_pool = None
redis_client = None

@app.on_event("startup")
async def startup():
    global nc, db_pool, s3, redis_client
    import asyncio
    import time
    import logging
    import resource
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Log memory usage (using resource module instead of psutil)
    try:
        memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux, ru_maxrss is in KB, on macOS it's in bytes
        memory_mb = memory_kb / 1024 if memory_kb > 100000 else memory_kb / (1024 * 1024)
        logger.info(f"Startup memory usage: {memory_mb:.2f}MB")
    except Exception as e:
        logger.info(f"Could not get memory usage: {e}")

    # NATS connection with authentication and retry
    logger.info("Starting NATS connection...")
    for attempt in range(5):
        try:
            nc = await nats.connect(
                os.getenv("NATS_URL"),
                user=os.getenv("NATS_USER"),
                password=os.getenv("NATS_PASSWORD")
            )
            logger.info("NATS connection successful")
            break
        except Exception as e:
            logger.error(f"NATS connection attempt {attempt + 1} failed: {e}")
            if attempt == 4:
                raise
            await asyncio.sleep(2 ** attempt)

    # PostgreSQL connection with retry
    logger.info("Starting PostgreSQL connection...")
    try:
        memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_mb = memory_kb / 1024 if memory_kb > 100000 else memory_kb / (1024 * 1024)
        logger.info(f"Memory before DB connection: {memory_mb:.2f}MB")
    except:
        pass
    for attempt in range(10):
        try:
            db_pool = await asyncpg.create_pool(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", 5432)),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                min_size=1,
                max_size=3
            )
            logger.info("PostgreSQL connection successful")
            break
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt == 9:
                raise
            await asyncio.sleep(2 ** min(attempt, 4))

    # S3 client
    logger.info("Initializing S3 client...")
    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv("AWS_ENDPOINT"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        use_ssl=True,
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )

    # Redis client with retry
    logger.info("Starting Redis connection...")
    for attempt in range(5):
        try:
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST"),
                port=6379,
                decode_responses=True
            )
            redis_client.ping()  # Test connection
            logger.info("Redis connection successful")
            break
        except Exception as e:
            logger.error(f"Redis connection attempt {attempt + 1} failed: {e}")
            if attempt == 4:
                raise
            await asyncio.sleep(2 ** attempt)

    # Initialize database schema
    logger.info("Initializing database schema...")
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY,
                filename VARCHAR(255),
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                text_preview TEXT
            )
        """)
    
    # Final memory check
    try:
        memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_mb = memory_kb / 1024 if memory_kb > 100000 else memory_kb / (1024 * 1024)
        logger.info(f"Startup complete. Final memory usage: {memory_mb:.2f}MB")
    except Exception as e:
        logger.info(f"Could not get final memory usage: {e}")

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    import logging
    logger = logging.getLogger(__name__)
    
    # Generate unique ID
    doc_id = str(uuid.uuid4())
    logger.info(f"Starting upload for file: {file.filename}, assigned ID: {doc_id}")

    # Save to S3
    s3.put_object(
        Bucket=os.getenv("AWS_BUCKET"),
        Key=f"documents/{doc_id}.pdf",
        Body=await file.read()
    )
    logger.info(f"File {doc_id} saved to S3 successfully")

    # Save metadata to PostgreSQL
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO documents (id, filename)
            VALUES ($1, $2)
        """, doc_id, file.filename)
    logger.info(f"File {doc_id} metadata saved to PostgreSQL")

    # Queue for processing
    await nc.publish("document.process", json.dumps({
        "id": doc_id,
        "filename": file.filename
    }).encode())
    logger.info(f"File {doc_id} queued for processing via NATS")

    return {"id": doc_id, "status": "queued"}

@app.get("/search")
async def search(query: str):
    # Check cache first
    cache_key = f"search:{query}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # Call Qdrant for vector search
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('QDRANT_URL')}/collections/documents/points/search",
            headers={
                "api-key": os.getenv("QDRANT_API_KEY")
            },
            json={
                "vector": [0.1] * 384,  # Dummy vector for demo
                "limit": 3,
                "with_payload": True
            }
        )

    result = {
        "query": query,
        "results": response.json().get("result", [])
    }

    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(result))

    return result

@app.get("/documents")
async def list_documents():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, filename, upload_date, processed
            FROM documents
            ORDER BY upload_date DESC
            LIMIT 10
        """)

    return [dict(row) for row in rows]

@app.get("/status")
async def status():
    services = {}

    # Check NATS
    services['nats'] = 'connected' if nc and nc.is_connected else 'disconnected'

    # Check PostgreSQL
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        services['postgresql'] = 'healthy'
    except:
        services['postgresql'] = 'unhealthy'

    # Check Qdrant
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{os.getenv('QDRANT_URL')}/",
                headers={"api-key": os.getenv("QDRANT_API_KEY")},
                timeout=2
            )
        services['qdrant'] = 'healthy'
    except:
        services['qdrant'] = 'unhealthy'

    # Check S3
    try:
        s3.list_buckets()
        services['storage'] = 'healthy'
    except:
        services['storage'] = 'unhealthy'

    # Check Redis
    try:
        redis_client.ping()
        services['cache'] = 'healthy'
    except:
        services['cache'] = 'unhealthy'

    return {"status": "operational", "services": services}