# External Sources

Integration of external data sources for legal knowledge ingestion.

## VisualexAPI Integration

VisualexAPI provides scrapers and tools for Italian and EU legal data.

**Original source**: `visualex/src/visualex_api/`
**Integrated into**: `backend/external_sources/visualex/`

### Components

#### Scrapers (`visualex/scrapers/`)
- **normattiva_scraper**: Scrape Italian legislation from Normattiva.it
- **brocardi_scraper**: Scrape legal commentary from Brocardi.it
- **eurlex_scraper**: Scrape EU legislation from EUR-Lex

#### Tools (`visualex/tools/`)
- **urngenerator**: Generate ELI-compliant URNs
- **norma**: Norma data structures and utilities
- **http_client**: HTTP client with retry logic
- **text_op**: Text processing utilities
- **treextractor**: HTML tree extraction

### Usage

```python
from backend.external_sources.visualex.scrapers import normattiva_scraper
from backend.external_sources.visualex.tools import urngenerator

# Generate URN
urn = urngenerator.generate_eli_urn(
    tipo_atto="codice civile",
    data="1942-03-16",
    numero_atto="262",
    articolo="1453"
)

# Scrape from Normattiva
result = normattiva_scraper.fetch_article(
    act_type="codice civile",
    article="1453"
)
```

### Deployment Modes

**Development (monolith)**: Direct import from `backend/external_sources/`
**Production (microservices)**: VisualexAPI runs as separate service

### Migration Path

For thesis: Use integrated version (monolith)
After thesis: Split into microservice at `visualex/` directory

### Maintenance

When updating VisualexAPI scrapers:
1. Update files in `visualex/src/visualex_api/`
2. Copy updated files to `backend/external_sources/visualex/`
3. Fix any import paths if needed
