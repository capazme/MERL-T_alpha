# RLCF Conference Q&A (Presenter Version)

Use this as a concise, presenter-friendly reference during the Q&A. Each answer includes a short summary, mechanisms, parameters, simple schemas, examples, risks, and evaluation metrics.

---

## 1) How do you prevent over‑reliance on credentials relative to performance?

**Short Answer**
- Cap credential weight, prioritize track record and recent performance, and enforce constitutional guardrails with ongoing calibration checks.

**Mechanism**
- Authority score: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`.
- Default weights: `α=0.3`, `β=0.5`, `γ=0.2` (track record dominates).
- Guardrail: configuration validation rejects `baseline_credentials > 0.6`.
- Performance-first reweighting: quality and calibration metrics drive periodic tuning of `β` and `γ`.

**Key Parameters**
- `α` (baseline credentials), `β` (track record), `γ` (recent performance).
- Smoothing for track record: `λ=0.95` → update factor `1-λ=0.05`.

**Schema (Policy Flow)**
```
Input: candidate weights (α, β, γ)
 → Check guardrails (α ≤ 0.6)
 → Evaluate calibration (ECE/Brier) under cross-validation
 → If calibration improves with lower α, raise β or γ
 → Freeze setting; log change; audit trail
```

**Example**
- A new PhD (`B_u` high) but limited track record: RLCF assigns influence primarily via `T_u` and `P_u`. Credentials help initial stability; sustained competence earns lasting authority.

**Risks & Mitigations**
- Risk: credential gaming or institutional bias → enforce caps, diversify credential mappings, audit correlations with correctness.
- Risk: over-correction penalizing legitimate expertise → monitor calibration vs. accuracy; use discipline-specific priors.

**Metrics & Evidence**
- Correlation between credentials and correctness (should be moderate, not dominant).
- Gini/Herfindahl of authority contributions (avoid concentration).
- Calibration: Expected Calibration Error (ECE), Brier score improvements after tuning.

---

## 2) What thresholds trigger uncertainty‑preserving outputs, and how are they chosen?

**Short Answer**
- Use normalized entropy `δ` to quantify disagreement; default threshold `τ=0.4`. Above `τ`, preserve dissent with structured alternatives; above `0.6`, trigger deeper discussion.

**Mechanism**
- Disagreement: `δ = -(1/log|P|) · Σ ρ(p) log ρ(p)` with authority-weighted probabilities `ρ(p)`.
- Decision: if `δ > τ`, output includes alternative positions with authority-weighted support and rationale.

**Key Parameters**
- `τ=0.4` (uncertainty threshold).
- High-disagreement heuristic: `δ > 0.6` → enriched discussion mode.

**Schema (Decision Flow)**
```
Aggregate feedback → compute authority-weighted probabilities ρ(p)
 → δ = entropy(probabilities, base=|P|)
 → if δ ≤ τ: CONSENSUS_OUTPUT
 → if τ < δ ≤ 0.6: UNCERTAINTY_OUTPUT (primary + alternatives)
 → if δ > 0.6: STRUCTURED_DISCUSSION (rationale clustering)
```

**Example**
- Three positions with weights `{0.5, 0.3, 0.2}` → `δ` is moderate; include minority views with support percentages.

**Choosing `τ`**
- Grid search on historical tasks to optimize a blend of accuracy, calibration, and user satisfaction.
- Domain-sensitive: safety-critical tasks use lower `τ` (more consensus), exploratory research uses higher `τ` (more pluralism).

**Risks & Mitigations**
- Too low `τ` suppresses valuable dissent → raise `τ` and monitor bias/coverage.
- Too high `τ` preserves noise → add authority filters and rationale quality checks.

**Metrics & Evidence**
- Confidence–accuracy calibration curves with/without uncertainty preservation.
- Minority coverage and stability across runs.
- Post-hoc user utility ratings for alternative positions.

---

## 3) How is bias measured across ideological and cultural dimensions?

**Short Answer**
- Use a multi-dimensional framework (ideological, methodological, cultural, geographical) with parity tests, content analysis, and cross-group accuracy/calibration; aggregate with a composite bias score.

**Mechanism**
- Curate group-specific evaluation sets (e.g., different schools of thought, regions, cultures).
- Measure per-group accuracy, calibration, and reasoning completeness; analyze content for framing and exclusion.
- Aggregate bias: `B_total = √(Σ b_i²)` across dimensions.

**Key Dimensions & Indicators**
- Ideological: performance parity across viewpoints; sentiment/framing analysis.
- Methodological: robustness across quantitative/qualitative tasks; consistency scores.
- Cultural: named entity coverage, cultural references, stereotype leakage tests.
- Geographical: jurisdictional correctness, regional data coverage, localization quality.

**Schema (Evaluation Protocol)**
```
Define groups → build balanced test sets →
 compute per-group metrics (Accuracy, ECE, F1, Reasoning length/completeness) →
 parity checks (Δ across groups), content bias checks →
 aggregate B_total; log and review in governance loop
```

**Example**
- Policy analysis prompts from multiple ideologies: ensure comparable accuracy and calibrated confidence; flag systematic underperformance.

**Risks & Mitigations**
- Proxy bias from imbalanced datasets → reweight or augment data; active sampling.
- Over-smoothing hides legitimate differences → report both parity and domain-specific baselines.

**Metrics & Evidence**
- Parity gaps (max Δ across groups), statistical significance tests.
- Calibration parity (ECE per group), coverage ratios.
- Qualitative audits: rationale diversity, presence of critical elements.

---

## 4) How do you adapt authority scoring across different disciplines?

**Short Answer**
- Keep the general form of the authority function but tune weight distributions and credential mappings per discipline under constitutional guardrails.

**Mechanism**
- Same formula; discipline-specific `α, β, γ` with caps maintained.
- Credential scoring uses configurable mappings and formulas (safe runtime evaluation).
- Track record stays central; decay `λ` can be adapted to task cadence.

**Key Parameters**
- Economics (example): stronger `β` for empirical replication; moderate `α` for degrees; `γ` tuned to recent forecasting performance.
- Anthropology (example): richer credential maps (fieldwork, publications), higher `γ` for recent ethnographic evaluations.

**Schema (Adaptation Workflow)**
```
Collect discipline norms → set priors for α, β, γ →
 configure credential mappings →
 run pilot studies; evaluate accuracy/calibration →
 adjust weights within guardrails; finalize and document
```

**Example**
- Legal vs. social sciences: legal domain keeps `β` high for demonstrated case analysis; social sciences broaden credential types with diverse methodological recognition.

**Risks & Mitigations**
- Overfitting to discipline idiosyncrasies → cross-discipline validation suite.
- Credential inflation → cap `α`, periodic audits against correctness.

**Metrics & Evidence**
- Discipline-specific calibration gains, accuracy improvements.
- Stability of authority over time vs. outcome quality.
- Cross-discipline generalization scores.

---

## 5) What are the computational trade‑offs of preserving dissent?

**Short Answer**
- Preserving dissent adds aggregation and structuring overhead; mitigate via caching, incremental computation, and top‑K summarization while maintaining uncertainty fidelity.

**Mechanism & Complexity**
- Aggregation: compute authority weights over `n` feedback items → `O(n)`.
- Disagreement: entropy over `|P|` positions → `O(|P|)`.
- Structuring alternatives: clustering rationales and summarization → typically `O(n log n)` with embedding-based grouping.

**Schema (Efficiency Strategy)**
```
Cache authority scores → incremental updates to δ →
 early exit when δ ≤ τ →
 top‑K alternative positions (K tunable) →
 summarize rationales with length/quality constraints
```

**Example**
- High‑volume feedback: cap alternatives to top‑K by authority weight; include links to full rationale sets for audit.

**Risks & Mitigations**
- Latency spikes → batching, streaming outputs, adjustable detail level.
- Information loss from aggressive pruning → expose provenance and allow drill‑down.

**Metrics & Evidence**
- Latency, memory footprint, throughput under varying `n` and `|P|`.
- Fidelity of uncertainty representation (agreement between full vs. pruned outputs).
- User utility ratings and audit completeness.

---

## Presenter Cheat Sheet (Quick Hits)

- Credentials vs. performance: cap `α`, prioritize `β`, tune `γ` with calibration.
- Uncertainty threshold: `τ=0.4` default; `δ>0.6` → structured discussion.
- Bias: evaluate multi-dimensional parity; aggregate `B_total` and audit content.
- Discipline adaptation: same formula, different `α/β/γ`, safe credential mapping.
- Computation: optimize with caching and top‑K; preserve provenance.

---

## References (for Q&A)

- Authority scoring weights and guardrails: default `α=0.3, β=0.5, γ=0.2`; cap for credentials at `0.6`.
- Disagreement and thresholds: normalized entropy `δ`; `τ=0.4`; high disagreement `>0.6`.
- Track record updating: exponential smoothing with `λ=0.95`.
- Bias aggregation: `B_total = √(Σ b_i²)` across dimensions.