# Dynamic Configuration System - Quick Start

## 🎯 Overview

Il sistema RLCF ora supporta **configurazione dinamica delle task** con hot-reload automatico! Puoi:

- ✅ **Aggiungere nuovi task types** senza riavviare il server
- ✅ **Modificare schemi** direttamente editando YAML o via API
- ✅ **Hot-reload automatico** quando modifichi i file
- ✅ **Backup automatici** prima di ogni modifica
- ✅ **Validazione robusta** per evitare configurazioni errate
- ✅ **Rollback** a configurazioni precedenti

---

## 🚀 Quick Start

### 1. Avvia il server

```bash
cd backend
uvicorn rlcf_framework.main:app --reload
```

Vedrai nel log:
```
[RLCF] Configuration hot-reload enabled
[RLCF] Watching: model_config.yaml, task_config.yaml
```

### 2. Verifica lo stato

```bash
curl http://localhost:8000/config/status | jq
```

Output:
```json
{
  "status": "active",
  "file_watching_enabled": true,
  "task_types_count": 11,
  "task_types": ["QA", "STATUTORY_RULE_QA", "RETRIEVAL_VALIDATION", ...]
}
```

### 3. Opzione A: Aggiungi Task Type via API

```bash
export ADMIN_API_KEY="supersecretkey"

curl -X POST http://localhost:8000/config/task/type \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{
    "task_type_name": "CONTRACT_REVIEW",
    "schema": {
      "input_data": {
        "contract_text": "str",
        "review_criteria": "List[str]"
      },
      "feedback_data": {
        "review_result": "str",
        "issues_found": "List[str]",
        "severity": "int"
      },
      "ground_truth_keys": ["review_result"]
    }
  }'
```

**Risultato immediato:**
- ✅ Backup automatico creato
- ✅ `task_config.yaml` aggiornato
- ✅ Configurazione ricaricata
- ✅ Nuovo task type disponibile

### 3. Opzione B: Modifica Manuale del YAML

```bash
# Apri l'editor
code merlt/rlcf_framework/task_config.yaml

# Aggiungi sotto task_types:
CONTRACT_REVIEW:
  input_data:
    contract_text: str
    review_criteria: List[str]
  feedback_data:
    review_result: str
    issues_found: List[str]
    severity: int
  ground_truth_keys:
    - review_result

# Salva (Ctrl+S)
```

**Vedrai nel log:**
```
[ConfigManager] Hot-reloaded: task_config.yaml
```

---

## 📚 Endpoint Principali

### Lista task types
```bash
curl http://localhost:8000/config/task/types
```

### Crea task type
```bash
curl -X POST http://localhost:8000/config/task/type \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{ ... }'
```

### Aggiorna task type
```bash
curl -X PUT http://localhost:8000/config/task/type/CONTRACT_REVIEW \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{ "schema": { ... } }'
```

### Elimina task type
```bash
curl -X DELETE http://localhost:8000/config/task/type/CONTRACT_REVIEW \
  -H "X-API-KEY: $ADMIN_API_KEY"
```

### Lista backups
```bash
curl http://localhost:8000/config/backups \
  -H "X-API-KEY: $ADMIN_API_KEY" | jq
```

### Restore backup
```bash
curl -X POST http://localhost:8000/config/backups/restore \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{ "backup_filename": "task_config_20250105_143052.yaml" }'
```

---

## 🧪 Testing

### Test automatico completo

```bash
./scripts/test_dynamic_config.sh
```

Questo script testa:
- ✅ Creazione task type
- ✅ Validazione schema
- ✅ Aggiornamento
- ✅ Eliminazione
- ✅ Backup system
- ✅ Gestione errori

### Test manuale hot-reload

**Terminal 1 - Server logs:**
```bash
cd backend
tail -f rlcf_detailed.log | grep ConfigManager
```

**Terminal 2 - Modifica YAML:**
```bash
# Modifica merlt/rlcf_framework/task_config.yaml
# Aggiungi/modifica un task type
```

**Terminal 1 - Vedrai:**
```
[ConfigManager] Hot-reloaded: task_config.yaml
```

---

## 🎨 Schema dei Task Types

### Struttura Base

```yaml
TASK_NAME:
  input_data:           # Dati in ingresso per la task
    field_name: str     # Tipo Python come stringa
    another_field: int
  feedback_data:        # Struttura del feedback
    result: str
    confidence: float
  ground_truth_keys:    # Campi da usare come ground truth
    - result
```

### Tipi Supportati

- `str` - Stringa
- `int` - Intero
- `float` - Float
- `bool` - Booleano
- `List[str]` - Lista di stringhe
- `List[int]` - Lista di interi
- `Dict[str, float]` - Dizionario chiave-valore
- Altri tipi Pydantic supportati

### Esempio Completo

```yaml
COMPLIANCE_ANALYSIS:
  input_data:
    regulation_text: str
    company_policy: str
    jurisdiction: str
    applicable_laws: List[str]
  feedback_data:
    is_compliant: bool
    violations: List[str]
    severity_score: int
    recommendations: str
    confidence_level: float
  ground_truth_keys:
    - is_compliant
    - violations
```

---

## 🔒 Sicurezza

### API Key

Tutti gli endpoint di configurazione richiedono autenticazione:

```bash
export ADMIN_API_KEY="your-secure-key-here"

curl -H "X-API-KEY: $ADMIN_API_KEY" ...
```

**Production:** Usa variabile d'ambiente `ADMIN_API_KEY`

### Validazione

Pydantic valida tutti gli schemi prima di applicarli:
- ✅ Struttura corretta
- ✅ Tipi validi
- ✅ Campi richiesti presenti

Configurazioni invalide vengono **rifiutate automaticamente**.

### Backup

Ogni modifica crea un backup automatico:
- 📁 `merlt/rlcf_framework/config_backups/`
- 🕒 Timestamp: `task_config_YYYYMMDD_HHMMSS.yaml`
- 🔄 Restore rapido via API

---

## 📖 Documentazione Completa

Vedi: **`docs/04-implementation/DYNAMIC_CONFIGURATION.md`**

Include:
- Architettura dettagliata
- API reference completa
- Use cases avanzati
- Troubleshooting
- Best practices

---

## 🐛 Troubleshooting

### Hot-reload non funziona

```bash
# 1. Verifica file watching
curl http://localhost:8000/config/status | jq .file_watching_enabled
# Dovrebbe essere: true

# 2. Controlla i log
tail -f merlt/rlcf_detailed.log | grep ConfigManager

# 3. Riavvia il server
# Ctrl+C
uvicorn rlcf_framework.main:app --reload
```

### Errore di validazione

```bash
# Schema non valido - esempio errore:
{
  "detail": "Validation failed: 1 validation error for TaskConfig
  task_types -> CUSTOM_TASK -> input_data
  value is not a valid dict (type=type_error.dict)"
}

# Fix: Assicurati che input_data sia un dizionario
{
  "input_data": {     # ← Deve essere un dict
    "field": "str"
  }
}
```

### Restore backup fallito

```bash
# 1. Lista backups disponibili
curl http://localhost:8000/config/backups \
  -H "X-API-KEY: $ADMIN_API_KEY" | jq

# 2. Usa il filename esatto dal response
curl -X POST http://localhost:8000/config/backups/restore \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{"backup_filename": "task_config_20250105_143052.yaml"}'
```

---

## 🚧 Limitazioni Attuali

1. **Handler Manuali:** I nuovi task types richiedono handler Python personalizzati per aggregazione/validazione. Il sistema valida gli schemi ma non genera automaticamente gli handler.

2. **Migration:** Modificare schemi di task esistenti non migra automaticamente le task già create nel database.

3. **UI:** Non c'è ancora un'interfaccia grafica per gestire le configurazioni (prevista per Phase 2).

---

## 🎯 Prossimi Passi

1. **Testa il sistema:**
   ```bash
   ./scripts/test_dynamic_config.sh
   ```

2. **Crea un task type personalizzato** per il tuo use case

3. **Monitora i logs** durante lo sviluppo:
   ```bash
   tail -f merlt/rlcf_detailed.log | grep -E "ConfigManager|RLCF"
   ```

4. **Leggi la documentazione completa** in `docs/04-implementation/DYNAMIC_CONFIGURATION.md`

---

## 💡 Esempi Pratici

### Use Case 1: Task di Compliance GDPR

```bash
curl -X POST http://localhost:8000/config/task/type \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{
    "task_type_name": "GDPR_COMPLIANCE_CHECK",
    "schema": {
      "input_data": {
        "data_processing_description": "str",
        "legal_basis": "str",
        "data_subjects": "List[str]"
      },
      "feedback_data": {
        "is_compliant": "bool",
        "article_violations": "List[str]",
        "recommendations": "str",
        "severity": "int"
      },
      "ground_truth_keys": ["is_compliant", "article_violations"]
    }
  }'
```

### Use Case 2: Analisi Contrattuale

```bash
curl -X POST http://localhost:8000/config/task/type \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{
    "task_type_name": "CONTRACT_CLAUSE_ANALYSIS",
    "schema": {
      "input_data": {
        "contract_text": "str",
        "clause_type": "str",
        "jurisdiction": "str"
      },
      "feedback_data": {
        "clause_interpretation": "str",
        "potential_issues": "List[str]",
        "enforceability_score": "float"
      },
      "ground_truth_keys": ["clause_interpretation"]
    }
  }'
```

---

**Sistema implementato e pronto all'uso! 🎉**

Per domande o problemi: consulta `docs/04-implementation/DYNAMIC_CONFIGURATION.md`
