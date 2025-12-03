# Experiments Documentation

> **Sistema di documentazione esperimenti per MERL-T**
> Ogni esperimento significativo viene documentato per la tesi e il percorso argomentativo.

---

## Struttura

```
docs/experiments/
├── README.md                    # Questo file
├── TEMPLATE.md                  # Template per nuovi esperimenti
├── INDEX.md                     # Indice cronologico esperimenti
│
├── EXP-001_ingestion_libro_iv/  # Primo esperimento: ingestion 887 articoli
│   ├── DESIGN.md                # Design e metodologia
│   ├── EXECUTION.md             # Log esecuzione
│   ├── RESULTS.md               # Risultati e metriche
│   └── ANALYSIS.md              # Analisi e conclusioni
│
├── EXP-002_xxx/                 # Esperimenti successivi...
└── ...
```

---

## Convenzioni

### Naming
- **EXP-NNN**: Numero progressivo a 3 cifre
- **Nome descrittivo**: snake_case, max 30 caratteri
- Esempio: `EXP-001_ingestion_libro_iv`

### Documenti per Esperimento

| File | Contenuto | Quando |
|------|-----------|--------|
| `DESIGN.md` | Ipotesi, metodologia, setup | Prima dell'esperimento |
| `EXECUTION.md` | Log real-time, comandi, errori | Durante l'esperimento |
| `RESULTS.md` | Metriche, output, dati grezzi | Subito dopo |
| `ANALYSIS.md` | Interpretazione, conclusioni, next steps | Post-elaborazione |

### Status Esperimento

```
[PLANNED]    → Design completato, pronto per esecuzione
[RUNNING]    → In corso
[COMPLETED]  → Terminato con successo
[FAILED]     → Terminato con errori (documentare cause)
[ABANDONED]  → Abbandonato (documentare motivazione)
```

---

## Best Practices

### 1. Riproducibilità
- Documentare **tutti** i comandi eseguiti
- Salvare versioni esatte delle dipendenze
- Includere git commit hash di partenza
- Screenshot/log per risultati non deterministici

### 2. Tracciabilità Accademica
- Collegare a Research Questions (RQ) della tesi
- Citare papers/metodologie di riferimento
- Distinguere fatti da interpretazioni
- Documentare anche i fallimenti (valuable per tesi)

### 3. Metriche Quantitative
Preferire metriche oggettive:
- Tempo di esecuzione
- Numero di record processati
- Errori/warning count
- Memory/CPU usage
- Copertura dataset

### 4. Versionamento
- Ogni esperimento in sottocartella dedicata
- Non modificare esperimenti passati (append-only)
- Se si ripete un esperimento, creare nuovo EXP-NNN

---

## Research Questions (RQ) di Riferimento

Dalla metodologia (`docs/08-iteration/INGESTION_METHODOLOGY.md`):

| RQ | Domanda |
|----|---------|
| RQ1 | Il chunking comma-level preserva l'integrità semantica? |
| RQ2 | La struttura gerarchica (Libro→Titolo→Articolo) migliora il retrieval? |
| RQ3 | L'enrichment Brocardi aggiunge valore informativo misurabile? |
| RQ4 | La Bridge Table riduce latenza rispetto a join runtime? |

---

## Quick Start

```bash
# Creare nuovo esperimento
cp -r docs/experiments/TEMPLATE.md docs/experiments/EXP-NNN_nome_esperimento/
cd docs/experiments/EXP-NNN_nome_esperimento/

# Rinominare e compilare
mv TEMPLATE.md DESIGN.md
# Editare DESIGN.md con ipotesi e metodologia

# Durante esecuzione
touch EXECUTION.md
# Documentare comandi e output

# Post-esecuzione
touch RESULTS.md ANALYSIS.md
# Compilare risultati e analisi
```

---

## Esperimenti Attivi

| ID | Nome | Status | Data | RQ |
|----|------|--------|------|-----|
| EXP-001 | ingestion_libro_iv | PLANNED | 2025-12-03 | RQ1, RQ2, RQ3 |

---

*Ultimo aggiornamento: 3 Dicembre 2025*
