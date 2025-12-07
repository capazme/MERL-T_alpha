# Reasoning Layer Architecture

**Implementation Status**: ✅ **COMPLETATO**
**Current Version**: v0.6.0
**Last Updated**: November 2025

**Implemented Components**:
- ✅ 4 Reasoning Experts: Literal Interpreter (450 LOC), Systemic-Teleological (500 LOC), Principles Balancer (550 LOC), Precedent Analyst (500 LOC)
- ✅ Synthesizer: Opinion synthesis with contradiction handling (1,100 LOC)
- ✅ Iteration Controller: Multi-turn reasoning with 6 stopping criteria (500 LOC)
- ✅ ExpertContext: Unified context structure for expert execution
- ✅ LangGraph Integration: Expert nodes, synthesis node, iteration loop
- ✅ Test Suite: Expert tests + 25+ iteration controller tests

**Code Location**: `merlt/orchestration/experts/`, `merlt/orchestration/iteration/`
**Tests**: `tests/orchestration/test_experts.py`, `test_iteration_controller.py`

---

## 1. Introduction

The **Reasoning Layer** is where MERL-T performs legal analysis by leveraging specialized **Reasoning Experts**, each grounded in distinct legal epistemologies. This layer consists of:

1. **4 Reasoning Experts** (Literal Interpreter, Systemic-Teleological, Principles Balancer, Precedent Analyst)
2. **Synthesizer** (combines expert outputs into unified answer)
3. **Iteration Controller** (decides when to stop or iterate)

**Design Principles**:
- **Epistemic Plurality**: Multiple legal reasoning paradigms coexist
- **LLM-Based Experts**: All experts are LLMs with specialized prompts (not separate models)
- **Traceable**: Full provenance of sources for every claim
- **Adaptive**: Expert selection guided by Router, refined via RLCF
- **Synthesis-Aware**: Experts designed to be combined (not standalone)

**Performance Targets**:
- Expert inference: < 3s per expert (LLM latency)
- Parallel expert execution: ~3s (if multiple experts called)
- Synthesis: < 2s (LLM)
- Total reasoning: < 5s (single iteration, 2 experts)

**Reference**: See `docs/02-methodology/legal-reasoning.md` for theoretical foundation.

---

## 2. Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│         INPUT FROM ORCHESTRATION LAYER                    │
│   QueryContext + EnrichedContext + RetrievalResult        │
└────────────────────────┬──────────────────────────────────┘
                         ↓
┌───────────────────────────────────────────────────────────┐
│              EXPERT SELECTION (from ExecutionPlan)        │
│   Router specified which experts to activate              │
└────────────────────────┬──────────────────────────────────┘
                         ↓
         ┌───────────────┴───────────────┐
         │   Parallel Expert Execution   │
         └───────────────┬───────────────┘
                         ↓
      ┌──────────────────┴──────────────────┐
      │                                     │
      ↓                                     ↓
┌────────────────┐                  ┌────────────────┐
│ Expert 1:      │                  │ Expert 2:      │
│ Literal        │                  │ Systemic-      │
│ Interpreter    │                  │ Teleological   │
└────────┬───────┘                  └────────┬───────┘
         │                                    │
         ↓                                    ↓
   ExpertOutput 1                       ExpertOutput 2
         │                                    │
         └────────────────┬───────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────┐
│                     SYNTHESIZER                           │
│   Combine expert outputs into unified answer              │
│   Mode: convergent (consensus) | divergent (perspectives) │
└────────────────────────┬──────────────────────────────────┘
                         ↓
              ProvisionalAnswer Object
              (with full provenance)
                         ↓
┌───────────────────────────────────────────────────────────┐
│                 ITERATION CONTROLLER                      │
│   Evaluate: Should we iterate or stop?                    │
│   - Check confidence scores                               │
│   - Check expert consensus                                │
│   - Check stop criteria from ExecutionPlan                │
└────────────────────────┬──────────────────────────────────┘
                         ↓
         ┌───────────────┴───────────────┐
         │                               │
         ↓                               ↓
    STOP (confidence high)        ITERATE (refine retrieval)
    Return FinalAnswer             └─→ Back to Router
```

**Key Characteristics**:
- Experts execute **in parallel** (independent reasoning)
- All experts are **LLM-based** (same model, different prompts)
- Synthesizer runs **after** all experts complete
- Iteration decision based on **confidence scores** + **consensus**

---

## 3. Expert Architecture

**Reference**: `docs/02-methodology/legal-reasoning.md` §6

All Reasoning Experts implement a **standard interface** and are grounded in specific legal epistemologies.

### 3.1 Abstract Expert Interface

**Expert Interface Specification**:

```json
{
  "expert_interface": {
    "endpoint": "{expert_base_url}/reason",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "X-Trace-ID": "{trace_id}"
    },
    "request_body": {
      "expert_type": "Literal_Interpreter | Systemic_Teleological | Principles_Balancer | Precedent_Analyst",
      "context": {
        "query_context": "QueryContext object",
        "enriched_context": "EnrichedContext object",
        "retrieval_result": "RetrievalResult object"
      },
      "parameters": {
        "temperature": 0.3,
        "max_tokens": 2000,
        "priority": "high | medium | low"
      }
    },
    "response_body": {
      "expert_type": "string",
      "interpretation": "string (main legal reasoning)",
      "rationale": "object (structured explanation)",
      "confidence": 0.0-1.0,
      "sources": [
        {
          "source_type": "norm | jurisprudence | doctrine",
          "source_id": "string",
          "citation": "string",
          "relevance": "string"
        }
      ],
      "limitations": "string (caveats, edge cases)",
      "trace_id": "{trace_id}",
      "execution_time_ms": 2800
    }
  }
}
```

---

### 3.2 Expert Selection Criteria

**Selection Matrix** (Router uses this logic):

| Query Intent | Complexity | Primary Expert | Secondary Experts |
|-------------|-----------|---------------|-------------------|
| **validità_atto** | Low (< 0.4) | Literal Interpreter | - |
| **validità_atto** | Medium (0.4-0.7) | Literal Interpreter | Systemic-Teleological |
| **validità_atto** | High (> 0.7) | Literal Interpreter | Systemic-Teleological, Precedent Analyst |
| **interpretazione_norma** | Any | Systemic-Teleological | Literal Interpreter |
| **bilanciamento_diritti** | Any | Principles Balancer | Systemic-Teleological |
| **evoluzione_giurisprudenziale** | Any | Precedent Analyst | Literal Interpreter |
| **conseguenze_giuridiche** | Low-Medium | Literal Interpreter | - |
| **conseguenze_giuridiche** | High | Literal Interpreter | Systemic-Teleological, Precedent Analyst |

**Example Router Decision**:

Query: "È valido un contratto firmato da un minorenne?"
- Intent: `validità_atto`
- Complexity: 0.62 (medium)
- **Selected Experts**: `[Literal_Interpreter]` (sufficient for medium complexity validity check)

Query: "Come si bilancia privacy vs libertà di stampa?"
- Intent: `bilanciamento_diritti`
- Complexity: 0.85 (high)
- **Selected Experts**: `[Principles_Balancer, Systemic_Teleological]`

---

### 3.3 Expert Output Schema

**Unified Output Format** (all experts return this structure):

```json
{
  "expert_output": {
    "trace_id": "EXP-LIT-20241103-abc123",
    "expert_type": "Literal_Interpreter",
    "interpretation": "Secondo l'Art. 2 c.c., la maggiore età si acquista al compimento del 18° anno. Un minorenne (persona sotto i 18 anni) è privo della capacità di agire (Art. 2 c.c.), e quindi non può validamente stipulare contratti. Il contratto firmato da un minorenne è annullabile ai sensi dell'Art. 1425 c.c. per difetto di capacità.",
    "rationale": {
      "legal_basis": [
        {
          "norm_id": "art_2_cc",
          "article": "2",
          "source": "Codice Civile",
          "provision": "La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti...",
          "application": "Definisce età per capacità di agire"
        },
        {
          "norm_id": "art_1425_cc",
          "article": "1425",
          "source": "Codice Civile",
          "provision": "Il contratto è annullabile se una delle parti era legalmente incapace di contrattare",
          "application": "Conseguenza giuridica: annullabilità"
        }
      ],
      "reasoning_steps": [
        "1. Identificazione capacità: Minorenne (< 18 anni) → Incapace di agire (Art. 2 c.c.)",
        "2. Applicazione norma: Contratto con incapace → Annullabile (Art. 1425 c.c.)",
        "3. Conclusione: Contratto non valido, annullabile su istanza di parte"
      ]
    },
    "confidence": 0.95,
    "confidence_factors": {
      "norm_clarity": 1.0,
      "jurisprudence_alignment": 0.9,
      "contextual_ambiguity": 0.1
    },
    "sources": [
      {
        "source_type": "norm",
        "source_id": "art_2_cc",
        "citation": "Art. 2 c.c.",
        "text": "La maggiore età è fissata al compimento del diciottesimo anno...",
        "relevance": "Definisce capacità di agire"
      },
      {
        "source_type": "norm",
        "source_id": "art_1425_cc",
        "citation": "Art. 1425 c.c.",
        "text": "Il contratto è annullabile se una delle parti era legalmente incapace...",
        "relevance": "Conseguenza giuridica per contratti con incapaci"
      }
    ],
    "limitations": "Analisi basata solo su interpretazione letterale. Non considera: (1) possibili eccezioni per contratti di minore importanza (Art. 1426 c.c.), (2) ratifica del contratto al raggiungimento maggiore età, (3) evoluzione giurisprudenziale su contratti vantaggiosi per il minore.",
    "metadata": {
      "llm_model": "gpt-4o",
      "temperature": 0.3,
      "tokens_used": 1200,
      "execution_time_ms": 2800
    }
  }
}
```

**Key Fields**:
- **interpretation**: Human-readable legal reasoning (Italian)
- **rationale**: Structured explanation with norms, steps, application
- **confidence**: 0.0-1.0 score (influences synthesis and iteration)
- **sources**: Full provenance (every claim traced to source)
- **limitations**: Expert acknowledges gaps in reasoning (epistemic humility)

---

## 4. Reasoning Experts

### 4.1 Literal Interpreter

**Epistemology**: **Positivismo Giuridico** (Legal Positivism)
- Law = Written text of norms
- Interpretation = Literal textual analysis
- Focus: What the law **says** (not why, not context)

**Component Interface**:

```json
{
  "component": "literal_interpreter",
  "type": "llm_based_reasoning_expert",
  "epistemology": "positivismo_giuridico",
  "activation_criteria": {
    "primary_intent": ["validità_atto", "requisiti_procedurali", "conseguenze_giuridiche"],
    "complexity": "< 0.7",
    "norm_clarity": "> 0.8"
  },
  "strengths": [
    "High precision for clear rules",
    "Fast (single-pass textual analysis)",
    "High confidence when norms are unambiguous"
  ],
  "limitations": [
    "Ignores ratio legis (purpose of law)",
    "Ignores jurisprudence trends",
    "Ignores constitutional principles",
    "Weak on ambiguous or incomplete norms"
  ]
}
```

**System Prompt** (simplified):

```
SYSTEM PROMPT:

You are a LITERAL INTERPRETER legal expert, grounded in Legal Positivism.

## Your Role
Analyze the user's legal query by performing **strict textual analysis** of the
relevant legal norms. Your interpretation must be based ONLY on the written text
of the law, without considering:
- The purpose or intent of the legislator (ratio legis)
- Case law or jurisprudence
- Constitutional principles (unless directly cited in the norm)
- Social or ethical considerations

## Reasoning Methodology
1. **Identify applicable norms**: From the provided context, select norms that
   directly address the query.
2. **Textual analysis**: Read the norm literally, focusing on:
   - Key terms and their definitions (as defined in law)
   - Grammatical structure (subject, verb, object)
   - Logical conditions (if-then, unless, provided that)
3. **Apply to facts**: Map the query facts to norm provisions.
4. **Conclude**: State the legal consequence based on literal reading.

## Output Format
Return JSON with:
- **interpretation**: Clear Italian text with your reasoning
- **rationale**: Structured breakdown (norms cited, reasoning steps, application)
- **confidence**: 0.0-1.0 (high if norm is clear, low if ambiguous)
- **sources**: Every norm cited with full text excerpt
- **limitations**: Acknowledge what you ignored (ratio legis, case law, etc.)

## Example
Query: "È valido un contratto verbale per la vendita di un immobile?"
Norm: Art. 1350 c.c. - "Devono farsi per atto pubblico o per scrittura privata,
sotto pena di nullità: ...1) i contratti che trasferiscono la proprietà di beni immobili"

Interpretation: "L'Art. 1350 c.c. prescrive la forma scritta **sotto pena di nullità**
per i contratti di vendita immobiliare. Un contratto verbale NON soddisfa questo requisito.
Conclusione: Il contratto verbale è **nullo** per difetto di forma (Art. 1418 c.c.)."

Confidence: 0.98 (norm is crystal clear, no ambiguity)

Limitations: "Non ho considerato: (1) ratio legis della forma scritta (tutela della certezza),
(2) giurisprudenza su eccezioni (es. contratti preliminari), (3) principi costituzionali."
```

**Input Context**:

```json
{
  "query_context": {
    "original_query": "È valido un contratto firmato da un minorenne?",
    "intent": {"primary": "validità_atto"},
    "complexity": {"score": 0.62}
  },
  "retrieval_result": {
    "api_results": {
      "norm_texts": [
        {
          "norm_id": "art_2_cc",
          "text": "La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa."
        },
        {
          "norm_id": "art_1425_cc",
          "text": "Il contratto è annullabile se una delle parti era legalmente incapace di contrattare."
        }
      ]
    }
  }
}
```

**Output Example**: See §3.3 Expert Output Schema above.

---

### 4.2 Systemic-Teleological Reasoner

**Epistemology**: **Finalismo Giuridico** (Legal Teleology)
- Law = System of norms with purpose
- Interpretation = Understanding ratio legis + systemic coherence
- Focus: **Why** the law exists, how norms fit together

**Component Interface**:

```json
{
  "component": "systemic_teleological_reasoner",
  "type": "llm_based_reasoning_expert",
  "epistemology": "finalismo_giuridico",
  "activation_criteria": {
    "primary_intent": ["interpretazione_norma", "lacune_ordinamento"],
    "complexity": "> 0.6",
    "norm_ambiguity": "> 0.5"
  },
  "strengths": [
    "Handles ambiguous norms well",
    "Considers purpose of legislation",
    "Systemic coherence analysis",
    "Fills legal gaps via analogy"
  ],
  "limitations": [
    "More subjective than literal interpretation",
    "Requires understanding of legislative intent (not always clear)",
    "Slower (multi-step analysis)"
  ]
}
```

**System Prompt** (simplified):

```
SYSTEM PROMPT:

You are a SYSTEMIC-TELEOLOGICAL REASONER, grounded in Legal Teleology.

## Your Role
Analyze the user's legal query by understanding:
1. **Ratio legis**: The PURPOSE behind the norm (why it was enacted)
2. **Systemic coherence**: How this norm fits within the broader legal system
3. **Teleological interpretation**: Interpret ambiguous text in light of purpose

## Reasoning Methodology
1. **Identify applicable norms**: Select norms from context.
2. **Ratio legis analysis**: For each norm, identify:
   - Legislative intent (why was this rule created?)
   - Values protected (public interest, private rights, etc.)
   - Historical context (if relevant)
3. **Systemic coherence**: Analyze how norm relates to:
   - Other norms in same code/law
   - Constitutional principles
   - General legal principles (good faith, proportionality, etc.)
4. **Teleological interpretation**: If norm is ambiguous:
   - Interpret in way that best achieves ratio legis
   - Prefer interpretation consistent with system coherence
5. **Conclude**: State legal consequence justified by purpose + coherence.

## Output Format
Return JSON with:
- **interpretation**: Clear Italian text with systemic-teleological reasoning
- **rationale**: Breakdown (norms, ratio legis, coherence analysis, application)
- **confidence**: 0.0-1.0 (lower if purpose unclear)
- **sources**: Norms + any doctrine/commentary on legislative intent
- **limitations**: Acknowledge uncertainty in ratio legis or coherence

## Example
Query: "Cosa significa 'giusta causa' nell'Art. 2119 c.c. (licenziamento)?"
Norm: Art. 2119 c.c. - "Ciascuno dei contraenti può recedere dal contratto prima
della scadenza del termine, se il contratto è a tempo determinato, o senza preavviso,
se il contratto è a tempo indeterminato, qualora si verifichi una causa che non
consenta la prosecuzione, anche provvisoria, del rapporto."

Systemic-Teleological Reasoning:
- **Ratio legis**: Bilanciare interessi del lavoratore (stabilità) vs datore di lavoro
  (flessibilità in caso di gravi violazioni). La "giusta causa" protegge entrambi,
  evitando che il rapporto prosegua quando è irrimediabilmente compromesso.
- **Systemic coherence**: Si collega all'Art. 1175 c.c. (correttezza) e 1375 c.c.
  (buona fede nell'esecuzione del contratto). Violazioni gravi di questi obblighi
  costituiscono giusta causa.
- **Teleological interpretation**: "Giusta causa" va interpretata come violazione
  così grave da rendere IMPOSSIBILE (non solo difficile) la prosecuzione del rapporto.
  Esempi: furto, violenza, insubordinazione grave.

Confidence: 0.75 (ratio legis chiara, ma applicazione ai casi concreti richiede
valutazione giurisprudenziale).
```

**Key Differences from Literal Interpreter**:
- Considers **why** the law exists (not just **what** it says)
- Uses **related norms** to build systemic understanding
- **Fills gaps** via analogical reasoning (when law is silent)

---

### 4.3 Principles Balancer

**Epistemology**: **Costituzionalismo** (Constitutionalism)
- Law = Hierarchy of norms (Costituzione > Legge > Regolamento)
- Interpretation = Balancing competing constitutional principles
- Focus: **Which principle prevails** in case of conflict

**Component Interface**:

```json
{
  "component": "principles_balancer",
  "type": "llm_based_reasoning_expert",
  "epistemology": "costituzionalismo",
  "activation_criteria": {
    "primary_intent": ["bilanciamento_diritti"],
    "complexity": "> 0.7",
    "constitutional_refs": "> 0"
  },
  "strengths": [
    "Handles principle conflicts (privacy vs free speech)",
    "Applies constitutional hierarchy",
    "Considers fundamental rights"
  ],
  "limitations": [
    "Requires deep constitutional knowledge",
    "Balancing is context-dependent (no fixed rules)",
    "Slower (multi-level analysis)"
  ]
}
```

**System Prompt** (simplified):

```
SYSTEM PROMPT:

You are a PRINCIPLES BALANCER, grounded in Constitutionalism.

## Your Role
Analyze the user's legal query when it involves **conflicts between constitutional
principles** or fundamental rights. Your task is to:
1. Identify competing principles/rights
2. Analyze their constitutional basis
3. Apply balancing test (proportionality, necessity, least restrictive means)
4. Conclude which principle prevails (or how to harmonize them)

## Reasoning Methodology
1. **Identify principles in conflict**: Extract from query (e.g., privacy vs free speech)
2. **Constitutional basis**: For each principle, cite constitutional articles:
   - Art. 2 Cost. (diritti inviolabili)
   - Art. 13-22 Cost. (libertà specifiche)
   - Art. 3 Cost. (uguaglianza)
   - etc.
3. **Hierarchical analysis**: Apply Gerarchia Kelseniana:
   - Costituzione > Legge Costituzionale > Legge Ordinaria > Regolamento
   - No ordinary law can violate Costituzione
4. **Balancing test** (proportionality):
   - **Legitimacy**: Is the limitation pursuing a legitimate goal?
   - **Necessity**: Is the limitation necessary to achieve the goal?
   - **Proportionality**: Is the limitation proportionate (minimal restriction)?
   - **Balancing**: Which principle, in this specific context, should prevail?
5. **Conclude**: State which principle prevails + justification.

## Output Format
Return JSON with:
- **interpretation**: Italian text with balancing analysis
- **rationale**: Breakdown (principles identified, constitutional basis, balancing test, conclusion)
- **confidence**: 0.0-1.0 (lower for novel conflicts without case law)
- **sources**: Constitutional articles + relevant Corte Costituzionale case law
- **limitations**: Acknowledge context-dependency of balancing

## Example
Query: "Un giornale può pubblicare foto di un personaggio pubblico in spiaggia senza consenso?"

Principles in Conflict:
- **Libertà di stampa** (Art. 21 Cost.): Right to inform the public
- **Diritto alla riservatezza** (Art. 2 Cost. + GDPR): Right to privacy

Constitutional Basis:
- Art. 21 Cost.: "Tutti hanno diritto di manifestare liberamente il proprio pensiero..."
- Art. 2 Cost.: "La Repubblica riconosce e garantisce i diritti inviolabili dell'uomo..."

Balancing Test:
1. **Legitimacy**: Publishing photo = exercise of Art. 21 (legit)
2. **Necessity**: Is it necessary to inform public? Depends on **public interest**:
   - If person is politician discussing beach policy → YES (public interest)
   - If person is celebrity on vacation → NO (private life, no public interest)
3. **Proportionality**: Photo in public place (beach) = less invasive than private home
4. **Balancing**:
   - IF public interest (e.g., political figure, relevant to public debate) → **Libertà di stampa prevails**
   - IF no public interest (private life) → **Diritto alla riservatezza prevails**

Conclusion: Depends on context. General rule: Public figures have reduced privacy
expectation, BUT only for matters of public interest. Photos of private life (vacation)
are protected even for public figures.

Confidence: 0.70 (balancing is context-dependent, requires case-by-case analysis)
```

**Key Technique**: **Proportionality Test** (Corte Costituzionale doctrine)
- Used by Italian Constitutional Court to balance rights
- Three-step test: Legitimacy → Necessity → Proportionality

---

### 4.4 Precedent Analyst

**Epistemology**: **Empirismo Giuridico** (Legal Empiricism)
- Law = What courts **actually do** (not just what statutes say)
- Interpretation = Analyzing case law trends and precedents
- Focus: **Judicial interpretation patterns**

**Component Interface**:

```json
{
  "component": "precedent_analyst",
  "type": "llm_based_reasoning_expert",
  "epistemology": "empirismo_giuridico",
  "activation_criteria": {
    "primary_intent": ["evoluzione_giurisprudenziale"],
    "complexity": "> 0.6",
    "jurisprudence_available": true
  },
  "strengths": [
    "Captures how courts actually interpret norms",
    "Identifies trends in case law",
    "Distinguishes binding vs persuasive precedents",
    "Predicts likely judicial outcome"
  ],
  "limitations": [
    "Requires access to case law database (VectorDB)",
    "Italian law is civil law (precedents less binding than common law)",
    "Slower (must analyze multiple cases)"
  ]
}
```

**System Prompt** (simplified):

```
SYSTEM PROMPT:

You are a PRECEDENT ANALYST, grounded in Legal Empiricism.

## Your Role
Analyze the user's legal query by examining **case law** (sentenze) to understand
how courts have **actually interpreted** the relevant norms. Your focus is on:
1. **Trends**: How has judicial interpretation evolved over time?
2. **Binding precedents**: Corte Costituzionale, Cassazione Sezioni Unite
3. **Persuasive precedents**: Cassazione ordinaria, lower courts
4. **Ratio decidendi**: The legal principle established by each case

## Reasoning Methodology
1. **Identify relevant case law**: From VectorDB retrieval results, select sentenze
   that address the same legal issue as the query.
2. **Chronological analysis**: Order cases by date to identify trends.
3. **Precedent hierarchy**:
   - **Corte Costituzionale**: Binding on all courts (erga omnes)
   - **Cassazione Sezioni Unite**: Binding on lower courts, highly persuasive for Cassazione
   - **Cassazione ordinaria**: Persuasive, but not binding (Italian civil law)
   - **Lower courts (TAR, Appello)**: Informative, but weak precedent value
4. **Ratio decidendi extraction**: For each case, identify the legal principle applied.
5. **Synthesize trend**: If multiple cases agree → Consolidated trend
                        If cases diverge → Identify split, explain reasons
6. **Conclude**: Predict likely judicial outcome based on precedent analysis.

## Output Format
Return JSON with:
- **interpretation**: Italian text with precedent analysis
- **rationale**: Breakdown (cases cited, ratio decidendi, trend analysis, prediction)
- **confidence**: 0.0-1.0 (high if trend is consolidated, low if cases diverge)
- **sources**: Every case cited with date, court, summary, ratio decidendi
- **limitations**: Acknowledge if case law is scarce or conflicting

## Example
Query: "Le clausole vessatorie nei contratti del consumatore sono sempre nulle?"
Norm: Art. 33 Codice del Consumo - "Le clausole vessatorie sono nulle ma il contratto
rimane valido per il resto."

Precedent Analysis:
- **Cassazione S.U. n. 12567/2015**: Ratio decidendi = "La nullità delle clausole
  vessatorie è **rilevabile d'ufficio** dal giudice, anche senza istanza di parte,
  in quanto tutela l'interesse generale del consumatore."
  → Binding precedent, consolidated trend.

- **Cassazione n. 8423/2018**: Ratio decidendi = "La vessatorietà va valutata **ex ante**
  (al momento della conclusione del contratto), non ex post (sulla base di eventi successivi)."
  → Confirms consolidated approach.

- **Cassazione n. 15476/2020**: Ratio decidendi = "Il consumatore può rinunciare
  alla tutela contro le clausole vessatorie **solo dopo** che gli sono state
  specificamente indicate e spiegate (requisito di consapevolezza)."
  → Recent evolution: enhanced consumer protection.

Trend: **Consolidato**. La giurisprudenza di legittimità è ferma nel:
1. Rilevabilità d'ufficio della nullità
2. Valutazione ex ante della vessatorietà
3. Rinuncia alla tutela solo se consapevole

Prediction: Alta probabilità che il giudice rilevi d'ufficio la nullità di clausole
vessatorie, anche senza istanza del consumatore.

Confidence: 0.88 (trend consolidato con Sezioni Unite + multiple ordinanze concordi)
```

**Precedent Hierarchy in Italian Law**:

| Court | Binding Force | Notes |
|-------|--------------|-------|
| **Corte Costituzionale** | **Binding (erga omnes)** | Declares laws unconstitutional |
| **Cassazione Sezioni Unite** | **Binding on lower courts**, highly persuasive for Cassazione | Resolves splits in case law |
| **Cassazione (ordinaria)** | **Persuasive** (not binding) | Most authoritative interpretation, but Italian civil law ≠ common law |
| **Corte di Appello** | Informative | Second instance |
| **Tribunale / TAR** | Weak | First instance |
| **CGUE (EU Court)** | **Binding on EU law matters** | Supremacy of EU law |

---

## 5. Synthesizer

**Reference**: `docs/02-methodology/legal-reasoning.md` §7

The Synthesizer combines outputs from multiple experts into a single, coherent answer.

### 5.1 Component Interface

```json
{
  "component": "synthesizer",
  "type": "llm_based_synthesis_engine",
  "interface": {
    "endpoint": "http://synthesizer:8030/synthesize",
    "input": {
      "expert_outputs": [
        {
          "expert_type": "Literal_Interpreter",
          "interpretation": "...",
          "confidence": 0.95,
          "sources": [...]
        },
        {
          "expert_type": "Systemic_Teleological",
          "interpretation": "...",
          "confidence": 0.78,
          "sources": [...]
        }
      ],
      "synthesis_mode": "convergent | divergent",
      "query_context": "QueryContext object"
    },
    "output": {
      "final_answer": "string (unified Italian text)",
      "synthesis_strategy": "string (how experts were combined)",
      "confidence": 0.0-1.0,
      "provenance": [
        {
          "claim": "string (specific claim in answer)",
          "sources": ["art_2_cc", "cass_2023_12345"],
          "expert_support": ["Literal_Interpreter", "Precedent_Analyst"]
        }
      ],
      "trace_id": "SYN-20241103-abc123",
      "execution_time_ms": 1800
    }
  }
}
```

---

### 5.2 Convergent Synthesis

**Use Case**: When experts **agree** on the answer (different reasoning, same conclusion).

**System Prompt** (simplified):

```
SYSTEM PROMPT:

You are a LEGAL SYNTHESIZER in CONVERGENT mode.

## Your Role
You receive outputs from multiple legal experts who analyzed the same query.
Your task is to **combine their insights into a single, coherent answer** that:
1. Presents the **consensus conclusion**
2. Integrates the **best reasoning** from each expert
3. Preserves **full provenance** (every claim traced to sources)
4. Acknowledges **minor differences** if any

## Synthesis Strategy (Convergent)
1. **Identify consensus**: All experts agree on conclusion? → Emphasize agreement.
2. **Combine rationales**: Integrate complementary reasoning:
   - Literal Interpreter provides **textual basis**
   - Systemic-Teleological provides **purpose and coherence**
   - Precedent Analyst provides **judicial confirmation**
3. **Structure answer**:
   - Introduction: Clear answer to query
   - Legal basis: Norms cited (with sources)
   - Reasoning: Step-by-step analysis
   - Conclusion: Final answer + confidence
4. **Provenance**: For every claim, list sources + which experts support it.

## Output Format
Return JSON with:
- **final_answer**: Unified Italian text
- **synthesis_strategy**: "convergent (consensus on conclusion)"
- **confidence**: Average of expert confidences (weighted by expert confidence)
- **provenance**: Every claim mapped to sources + expert support

## Example
Expert Outputs:
- **Literal Interpreter**: "Il contratto è annullabile per incapacità (Art. 1425 c.c.)" (confidence: 0.95)
- **Precedent Analyst**: "La giurisprudenza conferma: Cass. 12567/2020 = contratto con minore è annullabile" (confidence: 0.88)

Convergent Synthesis:
"Il contratto firmato da un minorenne **è annullabile** (Art. 1425 c.c.). La norma
prevede che il contratto concluso da persona legalmente incapace può essere annullato
su istanza di parte. Questa interpretazione è **confermata dalla giurisprudenza**:
la Cassazione (sent. 12567/2020) ha ribadito che l'incapacità di agire del minorenne
costituisce causa di annullabilità del contratto, tutelando così l'interesse del
soggetto vulnerabile.

Conclusione: Il contratto **NON è valido ab initio**, ma è annullabile. Può essere
impugnato dal minorenne (o dal suo rappresentante legale) entro 5 anni dal raggiungimento
della maggiore età (Art. 1442 c.c.)."

Confidence: 0.915 (average of 0.95 and 0.88)
```

---

### 5.3 Divergent Synthesis

**Use Case**: When experts **disagree** on the answer or provide complementary perspectives.

**System Prompt** (simplified):

```
SYSTEM PROMPT:

You are a LEGAL SYNTHESIZER in DIVERGENT mode.

## Your Role
You receive outputs from multiple legal experts who analyzed the same query.
Your task is to **present multiple valid perspectives** when experts diverge, because:
- The law is ambiguous or incomplete
- Different epistemologies yield different conclusions
- The query involves balancing competing principles

## Synthesis Strategy (Divergent)
1. **Acknowledge divergence**: "La risposta dipende dall'approccio interpretativo..."
2. **Present each perspective**:
   - Expert 1 (Literal): "Secondo l'interpretazione letterale..."
   - Expert 2 (Systemic): "Secondo l'interpretazione teleologica..."
3. **Compare perspectives**: Highlight differences in reasoning and conclusions.
4. **Indicate which is stronger** (if possible): Based on:
   - Precedent support
   - Constitutional alignment
   - Doctrinal consensus
5. **Conclude**: "La soluzione più probabile è X, ma Y è argomentabile."

## Output Format
Return JSON with:
- **final_answer**: Italian text presenting multiple perspectives
- **synthesis_strategy**: "divergent (multiple valid perspectives)"
- **confidence**: Lower than convergent (reflects ambiguity)
- **provenance**: Each perspective traced to sources + expert

## Example
Expert Outputs:
- **Literal Interpreter**: "L'Art. 1350 c.c. richiede forma scritta → Contratto verbale è **nullo**" (confidence: 0.95)
- **Systemic-Teleological**: "La ratio dell'Art. 1350 c.c. (certezza) può essere soddisfatta da prova documentale → Contratto verbale con prova scritta può essere **valido**" (confidence: 0.65)

Divergent Synthesis:
"La risposta dipende dall'approccio interpretativo adottato:

**Interpretazione letterale** (Art. 1350 c.c.): Il codice civile prescrive la forma
scritta **sotto pena di nullità** per i contratti immobiliari. Secondo questa lettura,
un contratto verbale è **nullo** per difetto di forma, indipendentemente dalla presenza
di prove documentali successive.

**Interpretazione teleologica**: La ratio della forma scritta è garantire **certezza**
del contratto. Se le parti hanno scambiato documenti (email, accordi parziali scritti)
che provano l'accordo, la finalità della norma è soddisfatta. Alcuni autori sostengono
che in questo caso il contratto potrebbe essere considerato **valido**, almeno come
contratto preliminare con obbligo di stipula definitiva.

**Orientamento prevalente**: La giurisprudenza di legittimità (Cassazione) segue
l'**interpretazione letterale**: la forma scritta ad substantiam non può essere sostituita
da prove documentali. La forma è requisito di validità, non di prova.

Conclusione: Il contratto verbale per la vendita di un immobile è **nullo** (Art. 1418 c.c.),
secondo l'orientamento prevalente. Tuttavia, se esistono documenti scritti che provano
l'accordo, è possibile sostenere l'esistenza di un **contratto preliminare** con obbligo
di stipula della forma definitiva."

Confidence: 0.72 (divergence lowers confidence, but precedent favors literal interpretation)
```

---

### 5.4 Provenance Preservation

**Key Requirement**: Every claim in the final answer must be **traceable to sources**.

**Provenance Schema**:

```json
{
  "provenance": [
    {
      "claim_id": "claim_001",
      "claim_text": "Il contratto firmato da un minorenne è annullabile",
      "sources": [
        {
          "source_type": "norm",
          "source_id": "art_1425_cc",
          "citation": "Art. 1425 c.c.",
          "excerpt": "Il contratto è annullabile se una delle parti era legalmente incapace di contrattare",
          "relevance": "Base normativa per annullabilità"
        },
        {
          "source_type": "jurisprudence",
          "source_id": "cass_2020_12567",
          "citation": "Cass. sent. 12567/2020",
          "excerpt": "L'incapacità di agire del minorenne costituisce causa di annullabilità del contratto",
          "relevance": "Conferma giurisprudenziale"
        }
      ],
      "expert_support": [
        {"expert": "Literal_Interpreter", "confidence": 0.95},
        {"expert": "Precedent_Analyst", "confidence": 0.88}
      ]
    },
    {
      "claim_id": "claim_002",
      "claim_text": "Il contratto può essere impugnato entro 5 anni dal raggiungimento della maggiore età",
      "sources": [
        {
          "source_type": "norm",
          "source_id": "art_1442_cc",
          "citation": "Art. 1442 c.c.",
          "excerpt": "L'azione di annullamento si prescrive in cinque anni...",
          "relevance": "Termine di prescrizione"
        }
      ],
      "expert_support": [
        {"expert": "Literal_Interpreter", "confidence": 0.95}
      ]
    }
  ]
}
```

**User-Facing Provenance** (in final answer):

```
Il contratto firmato da un minorenne **è annullabile** [1].

[1] Fonte: Art. 1425 c.c. ("Il contratto è annullabile se una delle parti era
    legalmente incapace di contrattare"), confermato da Cass. sent. 12567/2020.
```

---

## 6. Iteration Controller

**Reference**: `docs/02-methodology/legal-reasoning.md` §8

The Iteration Controller decides whether to stop (return final answer) or iterate (refine retrieval).

### 6.1 Stop Criteria Logic

**Decision Flow**:

```
┌────────────────────────────────────────────────────┐
│ Receive: ProvisionalAnswer + Expert Outputs        │
└─────────────────────┬──────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────────┐
│ Check 1: Is max_iterations reached?                │
│ (from ExecutionPlan.iteration_strategy)            │
└─────────────────────┬──────────────────────────────┘
                      ↓
              YES ─────────→ STOP (return answer)
              NO
                      ↓
┌────────────────────────────────────────────────────┐
│ Check 2: Is confidence >= min_confidence?          │
│ (threshold from ExecutionPlan, default: 0.85)      │
└─────────────────────┬──────────────────────────────┘
                      ↓
              YES ─────────→ STOP (high confidence)
              NO
                      ↓
┌────────────────────────────────────────────────────┐
│ Check 3: Do experts have consensus?                │
│ (all experts agree on conclusion?)                 │
└─────────────────────┬──────────────────────────────┘
                      ↓
              YES ─────────→ STOP (consensus reached)
              NO
                      ↓
┌────────────────────────────────────────────────────┐
│ Check 4: Is norm ambiguity low?                    │
│ (threshold from ExecutionPlan, default: < 0.2)     │
└─────────────────────┬──────────────────────────────┘
                      ↓
              YES ─────────→ STOP (norm is clear)
              NO
                      ↓
              ITERATE (refine retrieval)
              └─→ Generate new retrieval plan
                  └─→ Back to Orchestration Layer
```

**Stop Criteria Schema**:

```json
{
  "stop_criteria": {
    "max_iterations_reached": false,
    "confidence_threshold_met": false,
    "expert_consensus": false,
    "norm_ambiguity_low": false,
    "decision": "iterate",
    "iteration_plan": {
      "reason": "Low confidence (0.62 < 0.85) + expert divergence",
      "additional_retrieval": {
        "vectordb_agent": {
          "enabled": true,
          "task_type": "semantic_search",
          "parameters": {
            "query": "contratto minorenne annullamento giurisprudenza",
            "top_k": 10,
            "filters": {
              "document_type": "jurisprudence",
              "court": "Cassazione"
            }
          },
          "rationale": "Fetch case law to resolve divergence between literal and teleological interpretations"
        }
      }
    }
  }
}
```

---

### 6.2 Iteration Strategy

**Iteration Types**:

| Iteration Reason | Additional Retrieval | Expected Improvement |
|-----------------|---------------------|---------------------|
| **Low confidence** | VectorDB: More similar cases/doctrine | Increase confidence via additional support |
| **Expert divergence** | VectorDB: Case law to resolve split | Find precedent that settles divergence |
| **Norm ambiguity** | KG Agent: Related norms for context | Systemic coherence clarifies ambiguity |
| **Missing context** | API Agent: Fetch additional norm versions | Temporal context resolves multivigenza |

**Example Iteration**:

**Iteration 1**:
- Query: "È valido un contratto firmato da un minorenne?"
- Experts: Literal Interpreter (confidence: 0.95)
- Confidence: 0.95 → **STOP** (high confidence, single expert sufficient)

**Iteration 1 (different scenario)**:
- Query: "Quali sono i limiti alla libertà di stampa?"
- Experts: Literal Interpreter (confidence: 0.65), Systemic-Teleological (confidence: 0.70)
- Experts **diverge** on how to balance Art. 21 Cost. vs Art. 2 Cost.
- Confidence: 0.675 (< 0.85) → **ITERATE**
- New retrieval: VectorDB search for "libertà stampa bilanciamento privacy giurisprudenza"
- Additional expert: Principles Balancer (to resolve balancing)

**Iteration 2**:
- Experts: Literal + Systemic + Principles Balancer + Precedent Analyst
- Precedent Analyst finds Corte Costituzionale ruling on balancing
- Confidence: 0.88 (> 0.85) → **STOP**

**Performance**:
- Average iterations: 1.2 (most queries stop after 1 iteration)
- Max iterations: 3 (hardcoded limit to prevent infinite loops)
- Iteration overhead: ~3s (retrieval + expert inference)

---

## 7. Technology Mapping

### 7.1 LLM for Experts and Synthesizer

| Component | Technology | Rationale | Phase |
|-----------|-----------|-----------|-------|
| **All Experts** | GPT-4o | Best reasoning quality, structured output | 2-3 |
| **Synthesizer** | GPT-4o | Consistent model across pipeline | 2-3 |
| **Alternative** | Claude Sonnet 3.5 | Lower cost, comparable quality | 3+ |
| **Temperature** | 0.3 (experts), 0.2 (synthesizer) | Low temperature for deterministic legal reasoning | All |

**Key Requirement**: **Same LLM for all components** (simplifies deployment, reduces latency).

---

### 7.2 Infrastructure

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Expert Services** | FastAPI | Async, OpenAPI, type hints |
| **Parallelization** | Python asyncio + httpx | Native async for parallel expert calls |
| **Prompt Management** | Jinja2 templates | Structured prompt construction |
| **Observability** | OpenTelemetry | Distributed tracing across experts |

---

## 8. Docker Compose Architecture

### 8.1 Service Definitions

```yaml
version: '3.8'

services:
  # Reasoning Orchestrator (dispatches experts)
  reasoning-orchestrator:
    build: ./services/reasoning-orchestrator
    ports:
      - "8030:8000"
    environment:
      - EXPERT_LITERAL_URL=http://expert-literal:8000
      - EXPERT_SYSTEMIC_URL=http://expert-systemic:8000
      - EXPERT_PRINCIPLES_URL=http://expert-principles:8000
      - EXPERT_PRECEDENT_URL=http://expert-precedent:8000
      - SYNTHESIZER_URL=http://synthesizer:8000
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - expert-literal
      - expert-systemic
      - expert-principles
      - expert-precedent
      - synthesizer
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Expert: Literal Interpreter
  expert-literal:
    build: ./services/expert-literal
    environment:
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MODEL=gpt-4o
      - TEMPERATURE=0.3
      - MAX_TOKENS=2000
    deploy:
      replicas: 2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Expert: Systemic-Teleological
  expert-systemic:
    build: ./services/expert-systemic
    environment:
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MODEL=gpt-4o
      - TEMPERATURE=0.3
      - MAX_TOKENS=2000
    deploy:
      replicas: 2

  # Expert: Principles Balancer
  expert-principles:
    build: ./services/expert-principles
    environment:
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MODEL=gpt-4o
      - TEMPERATURE=0.3
      - MAX_TOKENS=2000
    deploy:
      replicas: 1

  # Expert: Precedent Analyst
  expert-precedent:
    build: ./services/expert-precedent
    environment:
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MODEL=gpt-4o
      - TEMPERATURE=0.3
      - MAX_TOKENS=2000
    deploy:
      replicas: 1

  # Synthesizer
  synthesizer:
    build: ./services/synthesizer
    environment:
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MODEL=gpt-4o
      - TEMPERATURE=0.2
      - MAX_TOKENS=3000
    deploy:
      replicas: 1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Iteration Controller
  iteration-controller:
    build: ./services/iteration-controller
    environment:
      - ROUTER_URL=http://router:8000
      - MIN_CONFIDENCE=0.85
      - MAX_ITERATIONS=3
    depends_on:
      - router
```

---

### 8.2 Network Topology

```
┌──────────────────────────────────────────────────────┐
│         Reasoning Layer Network                      │
│                                                      │
│  ┌───────────────────────────────────────────┐     │
│  │  Reasoning Orchestrator :8030             │     │
│  └──────────┬────────────────────────────────┘     │
│             │                                       │
│             ├──────────┬──────────┬──────────┬─────┤
│             │          │          │          │     │
│             ↓          ↓          ↓          ↓     │
│  ┌──────────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐│
│  │ Literal      │ │Systemic │ │Principles│ │Precedent
│  │ Interpreter  │ │Teleolog.│ │Balancer │ │Analyst││
│  │ (×2 replicas)│ │(×2)     │ │(×1)     │ │(×1)  ││
│  └──────────────┘ └─────────┘ └─────────┘ └──────┘│
│                                                      │
│             ↓                                        │
│  ┌──────────────────────────────────────────┐      │
│  │  Synthesizer :8031                       │      │
│  └──────────────────────────────────────────┘      │
│                                                      │
│             ↓                                        │
│  ┌──────────────────────────────────────────┐      │
│  │  Iteration Controller :8032              │      │
│  └──────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────┘

External Access:
- Reasoning Orchestrator: http://localhost:8030
```

---

## 9. Error Handling & Resilience

### 9.1 Expert Failure Handling

**Expert Timeout**:
- Timeout per expert: 10s (LLM calls can be slow)
- If timeout → Mark expert as `status: "timeout"`, continue with other experts
- Partial results OK (1/2 experts succeed → Synthesizer can still work)

**Expert LLM Error**:
- Retry 2 times with exponential backoff (2s, 4s)
- If all retries fail → Skip expert, log error
- If **all experts fail** → CRITICAL ERROR, return error to user

**Minimum Expert Requirement**:
- At least **1 expert** must succeed for synthesis to proceed
- If 0 experts succeed → Return error: "Unable to perform legal analysis"

---

### 9.2 Synthesizer Failure Handling

**Synthesizer Timeout**:
- Timeout: 10s
- Retry 2 times
- If all retries fail → Return error to user (cannot proceed without synthesis)

**Invalid Synthesis Output**:
- If Synthesizer returns malformed JSON → Retry with stricter JSON Schema enforcement
- If still fails → Return raw expert outputs to user (degraded mode)

---

## 10. Performance Characteristics

### 10.1 Latency Breakdown

```
Total Reasoning Latency: ~5s (P95, 2 experts + synthesis)

┌────────────────────────────────────────────────┐
│ Expert Execution (parallel): 3s                │
│ ├─ Expert 1 (Literal): 2.8s                    │
│ ├─ Expert 2 (Systemic): 3.0s (bottleneck)      │
│ └─ Parallel: max(2.8, 3.0) = 3.0s             │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ Synthesis: 1.8s                                │
│ ├─ Prompt construction: 100ms                  │
│ ├─ LLM API call: 1.5s                          │
│ └─ Provenance assembly: 200ms                  │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ Iteration Decision: 20ms                       │
└────────────────────────────────────────────────┘

Total: 3.0s + 1.8s + 0.02s = 4.82s (average)
       5.2s (P95, includes retry overhead)
```

---

### 10.2 Resource Requirements

**Expert Service** (per instance):
- CPU: 1 core (I/O bound, waiting on LLM)
- RAM: 512MB
- Storage: 100MB (prompt templates)

**Synthesizer**:
- CPU: 1 core
- RAM: 512MB
- Storage: 100MB

**Scaling**:
- **Horizontal**: Scale expert replicas (2x Literal + 2x Systemic for common use cases)
- **Vertical**: Not applicable (LLM latency is external bottleneck)

---

## 11. Cross-References

### Section 02 Methodology
- **Legal Reasoning**: `docs/02-methodology/legal-reasoning.md`
  - §6: Expert Epistemologies (Positivism, Teleology, Constitutionalism, Empiricism)
  - §7: Synthesizer (convergent vs divergent modes)
  - §8: Iteration Controller (stop criteria)

### Section 03 Architecture
- **Orchestration Layer**: `docs/03-architecture/02-orchestration-layer.md`
  - Reasoning Layer consumes RetrievalResult from Orchestration Layer

- **Storage Layer**: `docs/03-architecture/04-storage-layer.md` (next)
  - VectorDB provides case law for Precedent Analyst

### Section 04 Implementation
- **Expert Services**: `docs/04-implementation/expert-services.md` (future)
- **Synthesizer Service**: `docs/04-implementation/synthesizer-service.md` (future)

---

## 12. Appendices

### A. Observability

**Logging**:
- **Experts**: Log interpretation + confidence + sources used
- **Synthesizer**: Log synthesis strategy + provenance
- **Format**: JSON structured logs with trace_id

**Metrics**:
- **Expert latency**: Per-expert LLM latency (P50, P95, P99)
- **Confidence distribution**: Histogram of expert confidence scores
- **Synthesis mode distribution**: Convergent vs divergent frequency
- **Iteration rate**: % of queries that iterate (goal: < 20%)

**Tracing**:
- **OpenTelemetry**: Full distributed tracing
- **Spans**: Reasoning Orchestrator (parent) → Experts (children, parallel) → Synthesizer (child)

---

### B. Security

**Authentication**:
- **Internal**: Mutual TLS between Reasoning Orchestrator ↔ Experts ↔ Synthesizer
- **External**: Reasoning Layer accessed only by Router (internal service)

**PII Protection**:
- No PII logging in expert outputs (queries anonymized before storage)

---

### C. Scalability

**Horizontal Scaling**:
- **Experts**: Scale independently based on usage (e.g., 5x Literal, 2x Systemic)
- **Synthesizer**: Single instance sufficient (< 1s latency)

**Auto-Scaling**:
- **Kubernetes HPA**: Scale based on LLM queue depth (target: < 5 queued requests per replica)

---

**Document Version**: 1.0
**Last Updated**: 2024-11-03
**Status**: ✅ Complete
