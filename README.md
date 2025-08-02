# Zerops RAG Infrastructure Example

A **hello-world demonstration** showing how [Zerops](https://zerops.io) handles the infrastructure complexity of RAG (Retrieval Augmented Generation) applications — so you can see how to integrate it into your own projects.

[![Deploy to Zerops](https://github.com/zeropsio/recipe-shared-assets/blob/main/deploy-button/green/deploy-button.svg)](https://app.zerops.io/recipe/rag-starter)

## What This Is (And Isn't)

**This is**: A minimal example demonstrating Zerops' capabilities for AI/LLM infrastructure  
**This isn't**: A RAG starter template or production-ready application

We intentionally kept the AI logic dummy-simple (first 500 chars, fake embeddings) to focus on what matters: **showing how Zerops eliminates DevOps complexity**.

## The Infrastructure Challenge

Modern RAG applications need:
- Vector database (Qdrant)
- Relational database (PostgreSQL)  
- Caching layer (Valkey/Redis)
- Message queue (NATS)
- Object storage (S3-compatible)
- API service + Workers
- Load balancing, SSL, scaling, monitoring...

Setting this up traditionally requires extensive DevOps knowledge. With Zerops, it's just YAML configuration.

## What This Example Shows

### 1. One-Click Infrastructure

Deploy 8 interconnected services in 60 seconds:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Qdrant    │     │ PostgreSQL  │     │   Valkey    │
│ (vectors)   │     │ (metadata)  │     │  (cache)    │
└─────────────┘     └─────────────┘     └─────────────┘
       ↑                    ↑                    ↑
       └────────────────────┼────────────────────┘
                           │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  FastAPI    │────▶│    NATS     │────▶│   Worker    │
│   (API)     │     │  (queue)    │     │ (processor) │
└─────────────┘     └─────────────┘     └─────────────┘
       ↑                                         │
       │                                         ▼
┌─────────────┐                         ┌─────────────┐
│  Dashboard  │                         │     S3      │
│   (web)     │                         │  (storage)  │
└─────────────┘                         └─────────────┘
```

### 2. Service Auto-Configuration

See how Zerops automatically wires services together using environment variables:

```python
# PostgreSQL connection - no manual config needed
db_pool = await asyncpg.create_pool(
    host=os.getenv("DB_HOST"),  # Zerops provides this
    password=os.getenv("DB_PASSWORD")  # And this
)

# Same for Redis, S3, NATS, Qdrant...
```

### 3. Build & Deploy Pipeline

The [`zerops.yml`](./zerops.yml) shows how to:
- Define build and runtime environments
- Configure auto-scaling
- Set up zero-downtime deployments

### 4. Development Workflow

Local development using cloud services:

```bash
# Connect to project's private network
zcli vpn up

# Get all service credentials
zcli env --dotenv > .env

# Your local code now uses Zerops databases
```

### 5. Production Patterns

- Async processing with queues
- Caching strategies  
- Service discovery
- High availability options

## Quick Demo

1. **Deploy**: Click the button above (60 seconds)
2. **Upload**: Try uploading a document via the dashboard
3. **Search**: See how the services interact
4. **Explore**: Check logs, metrics, and service details in Zerops dashboard

## Key Files to Examine

| File | What It Demonstrates |
|------|---------------------|
| [`zerops-project-import.yml`](./zerops-project-import.yml) | Development environment setup |
| [`zerops-project-production-import.yml`](./zerops-project-production-import.yml) | Production HA configuration |
| [`zerops.yml`](./zerops.yml) | Build & deploy pipeline |
| [`api/main.py`](./api/main.py) | Service integration patterns |

## Understanding the Integration

### Project Import Structure

```yaml
project:
  name: rag-demo
  envVariables:
    # Zerops auto-references service credentials
    DB_HOST: ${db_hostname}
    QDRANT_URL: ${qdrant_connectionString}
    # ... automatic for all services

services:
  - hostname: db
    type: postgresql@16
    mode: HA  # or NON_HA
```

### Build Configuration

```yaml
# From zerops.yml
- setup: api
  build:
    deployFiles: ./api/~
  run:
    base: python@3.11
    ports:
      - port: 8000
        httpSupport: true
```

## Cost Example

- **Development** (non-HA): ~$10/month
- **Production** (full HA): ~$30/month
- **Scaling**: Pay per minute for actual usage

2-3x cheaper than comparable platforms, with no seat limits or tier restrictions.

## The Zerops Advantage

This example demonstrates how Zerops provides:

✅ **Complete infrastructure** in one YAML file  
✅ **Automatic service wiring** via environment variables  
✅ **Built-in CI/CD** with zero-downtime deploys  
✅ **Development/production parity** with different resource allocations  
✅ **No DevOps required** — focus on your application logic  

## Learn More

- **Full Article**: [The Perfect Cloud Platform for Development and Production of AI/LLM Apps](https://blog.zerops.io/posts/the-perfect-cloud-platform-for-development-and-production-of-ai-llm-apps)
- **Documentation**: [Zerops Docs](https://docs.zerops.io)
- **YAML Specification**: [zerops.yml Reference](https://docs.zerops.io/zerops-yaml/specification)
- **Community**: [Discord](https://discord.gg/zeropsio)

---

This example shows how Zerops handles infrastructure complexity. Use these patterns in your own RAG applications to eliminate DevOps overhead and focus on building your AI features.