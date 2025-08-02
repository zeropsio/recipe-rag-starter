# Zerops RAG Infrastructure Starter

A working example of multi-service architecture for document search applications on [Zerops](https://zerops.io). This starter provides all the infrastructure you need for a RAG application, with simplified AI logic that you'll replace with your own implementation.

[![Deploy to Zerops](https://github.com/zeropsio/recipe-shared-assets/blob/main/deploy-button/green/deploy-button.svg)](https://app.zerops.io/recipe/rag-starter)

## What This Is

This is a "hello-world" complexity app that demonstrates how Zerops handles the infrastructure complexity of AI/LLM applications. It provides:

- **Complete working infrastructure**: 8 interconnected services deployed and configured
- **Simplified AI logic**: Basic placeholders you'll replace with your actual implementation  
- **Production patterns**: Async processing, caching, service discovery - all handled by Zerops
- **Zero DevOps required**: Zerops manages the infrastructure, you focus on your app

## Why This Starter?

Building RAG applications requires complex infrastructure:
- **Vector database** for embeddings (Qdrant)
- **Relational database** for metadata (PostgreSQL) 
- **Key-value cache** (Valkey/Redis)
- **Message queue** for async processing (NATS)
- **Object storage** for documents (S3-compatible)
- **API service** (FastAPI)
- **Background workers**
- **Web dashboard**

Without DevOps knowledge, this is overwhelming. With DevOps knowledge, it's time-consuming. Zerops handles all of this - deploy with one click, focus on your AI logic.

## Architecture

```
Upload → API → S3 Storage
           ↓
         NATS Queue
           ↓
     Background Worker → Qdrant (vectors)
           ↓                ↑
      PostgreSQL        Search API
      (metadata)       (with Redis cache)
```

## What Zerops Handles For You

- ✅ **Service orchestration**: All 8 services configured and networked
- ✅ **Automatic scaling**: Both horizontal and vertical, based on load
- ✅ **Service discovery**: Connection strings auto-injected as env vars
- ✅ **Build & deploy pipeline**: Zero-downtime deployments from Git
- ✅ **High availability**: Optional HA mode for all services
- ✅ **Networking**: Private network with L3/L7 load balancers
- ✅ **SSL/TLS**: Automatic certificate management
- ✅ **Monitoring**: Logs, metrics, and health checks
- ✅ **Developer experience**: VPN access, web terminal, one-click rollbacks

## What You Build

| Provided (Working Demo) | Your Implementation |
|------------------------|-------------------|
| First 500 chars of files | Real PDF/DOCX parsing with libraries of your choice |
| Basic sentence transformer | Your embedding model (OpenAI, Cohere, custom) |
| Dummy search vectors | Actual query embedding logic |
| No text chunking | Your chunking strategy |
| No LLM integration | Your choice of LLM (OpenAI, Anthropic, Llama, etc) |

## Quick Start

### Deploy to Zerops (Recommended)
Click the deploy button. In 60 seconds, your complete infrastructure is running.

### Local Development

Zerops enables true hybrid development - run your code locally while using cloud services:

```bash
# Connect to your Zerops project's private network
zcli vpn up

# Download all service connection strings as env vars
cd api && zcli env > .env

# Install and run locally
uv venv && uv pip install -r requirements.txt
uv run uvicorn main:app --reload
```

Your local API now connects to Zerops-hosted databases and services.

## Service Connections

Zerops automatically provides connection details as environment variables:

```python
# PostgreSQL - Zerops provides DB_HOST, DB_USER, DB_PASSWORD
db_pool = await asyncpg.create_pool(
    host=os.getenv("DB_HOST"),
    password=os.getenv("DB_PASSWORD")
)

# Redis - Zerops provides REDIS_HOST
redis_client = redis.Redis(host=os.getenv("REDIS_HOST"))

# S3 - Zerops provides AWS_ENDPOINT, AWS_ACCESS_KEY_ID
s3 = boto3.client('s3', endpoint_url=os.getenv("AWS_ENDPOINT"))

# NATS - Zerops provides NATS_URL, NATS_USER, NATS_PASSWORD  
nc = await nats.connect(os.getenv("NATS_URL"))

# Qdrant - Zerops provides QDRANT_URL, QDRANT_API_KEY
```

No manual configuration needed - Zerops handles service discovery.

## Integration Points

Replace the demo code with your implementation:

| File | Line | Current Demo | Your Code |
|------|------|--------------|-----------|
| `processor/processor.py:79` | Text extraction | `content[:500]` | PDF parsing library |
| `processor/processor.py:83` | Embeddings | `all-MiniLM-L6-v2` | Your embedding model |
| `api/main.py:195` | Query vectors | `[0.1] * 384` | Real query embeddings |
| New endpoint | Generation | None | LLM completion endpoint |

## Production vs Development

Zerops ensures complete environment parity:

- **Same infrastructure**: Dev and prod use identical service setup
- **Different resources**: Dev uses minimal resources, prod scales up
- **Same deployment**: Both use identical `zerops.yml` configuration
- **Cost-efficient**: Dev ~$10/mo, Production ~$30/mo with HA

## Project Structure

```
api/          # FastAPI service
processor/    # Document processing worker
dashboard/    # Web UI
zerops.yml    # Defines build & deploy for all services
```

## Scaling Without Complexity

Zerops handles scaling automatically:
- Workers scale from 0.125GB to 48GB RAM as needed
- API scales horizontally based on requests
- Databases run in HA mode across availability zones
- Pay per minute for actual usage

## Cost

- **Development**: ~$10/month (or ~$2/month for 8-hour workdays)
- **Production**: ~$30/month for full HA setup
- **2-3x cheaper** than comparable PaaS platforms
- **Transparent**: Per-minute billing, no hidden costs

## Learn More

- [Building RAG apps on Zerops - Full Tutorial](https://blog.zerops.io/posts/perfect-platform-for-ai-llm-apps)
- [Zerops Documentation](https://docs.zerops.io)
- [Discord Community](https://discord.gg/zerops)

---

Built for [Zerops](https://zerops.io) — focus on your app, not the infrastructure.