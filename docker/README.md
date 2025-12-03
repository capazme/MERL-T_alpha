# Docker Containers

Dockerfiles per deploy distribuito (multi-container).

## Modalità di Deploy

### Monolith (Development)
```bash
# Avvia solo i database
docker-compose -f docker-compose.dev.yml up -d

# Applicazione gira nativa (Python)
uvicorn backend.orchestration.api.main:app --reload
```

### Distributed (Production)
```bash
# Avvia tutti i container
export MERL_T_MODE=distributed
docker-compose -f docker-compose.distributed.yml up -d
```

## Container Disponibili

| Container | Dockerfile | Porta | Scopo |
|-----------|------------|-------|-------|
| `storage-service` | Dockerfile.storage | 8001 | API unificata per database |
| `expert-*` | Dockerfile.expert | 8010-8013 | Expert reasoning services |
| `orchestration` | Dockerfile.orchestration | 8000 | Router + Gating + Synthesis |
| `rlcf-service` | Dockerfile.rlcf | 8002 | Learning layer |

## Variabili d'Ambiente

Creare `.env.production`:
```env
POSTGRES_PASSWORD=...
OPENROUTER_API_KEY=...
MERL_T_MODE=distributed
```

## Note

- I Dockerfile sono placeholder per v2
- Implementare quando serve scalabilità reale
- Per ora usare monolith mode
