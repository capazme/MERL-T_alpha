# RLCF Four Pillars — Projection-Ready Schematics

Use these one-slide schemas to communicate the core pillars clearly. Keep delivery to ~30–45 seconds per block.

---

## Pillar 1 — Dynamic Authority Scoring

**One‑Slide Schema**
```
[Credentials B_u] --(α)--> 
                        
[Track Record T_u(t-1)] --(β)-->  [Authority A_u(t)]
                        
[Recent Performance P_u(t)] --(γ)-->
```

**Key Mechanics**
- Authority: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)` with `α+β+γ=1`.
- Defaults: `α=0.3`, `β=0.5`, `γ=0.2` (track record dominates).
- Track record smoothing: `T_u(t) = λ·T_u(t-1) + (1-λ)·Q_u(t)`, `λ=0.95`.

**Talking Points**
- Authority is earned: performance and track record outweigh credentials.
- Adapts fast via `P_u(t)` while preserving stability via `T_u(t-1)`.
- Guardrails cap credential influence; changes are auditable.

**Parameters to Show**
- `α, β, γ` (weights), `λ` (decay), quality `Q_u(t)` components.

**Example**
- New PhD: higher `B_u`, but influence mostly from `T_u`, `P_u` as results accrue.

---

## Pillar 2 — Uncertainty‑Preserving Aggregation

**One‑Slide Schema**
```
Feedback f_i  →  Authority a_i  →  Position weights ρ(p)  →  Entropy δ
                                         │
                         ┌───────────────┴────────────────┐
                         │                                │
                     if δ ≤ τ                        if δ > τ
                 CONSENSUS OUTPUT            UNCERTAINTY OUTPUT
                                        (Primary + Alternatives,
                                      support %, rationale excerpts)
```

**Key Mechanics**
- Disagreement: `δ = -(1/log|P|) · Σ ρ(p) log ρ(p)` (normalized entropy).
- Thresholds: default `τ=0.4`; high disagreement `δ>0.6` → structured discussion.

**Talking Points**
- Disagreement is information; we preserve pluralism when warranted.
- Outputs include alternative positions with authority‑weighted support.
- Better confidence calibration by modeling dissent.

**Parameters to Show**
- `τ` (uncertainty threshold), `δ` (normalized entropy), `|P|` (#positions).

**Example**
- Positions `{0.5, 0.3, 0.2}` → `δ` moderate → show primary plus two alternatives.

---

## Pillar 3 — Community Governance & Transparent Validation

**One‑Slide Schema**
```
[Configuration / Policy Proposal]
          │
          ▼
[Constitutional Validation]
  - Caps (e.g., α ≤ 0.6)
  - Threshold safeguards (e.g., τ ≥ 0.1)
          │
          ▼
[Apply + Audit Log]
          │
          ▼
[Runtime Hot‑Reload + Monitoring]
```

**Key Mechanics**
- Parameter updates validated against core principles before adoption.
- Changes logged; system hot‑reloads with auditability.
- Prevents harmful drift; supports A/B research.

**Talking Points**
- Transparent, reproducible governance; every change is traceable.
- Safety guardrails enforce methodological rigor.
- Domain adaptation within constitutional limits.

**Controls to Show**
- Credential cap: e.g., `baseline_credentials ≤ 0.6`.
- Minimum disagreement threshold: avoids suppressing dialectics.

**Example**
- Proposal to raise `β` after calibration study → validated, applied, logged.

---

## Pillar 4 — Devil’s Advocate System

**One‑Slide Schema**
```
[Eligible Evaluators |E|] → Filter (authority > 0.5)
           │
           ▼
Probabilistic assignment: P(advocate) = min(0.1, 3/|E|)
           │
           ▼
[Critical Prompts + Counter‑Arguments]
           │
           ▼
[Effectiveness Metrics]
 - Diversity introduced
 - Engagement score
 - Calibration & robustness gains
```

**Key Mechanics**
- Randomized assignment ensures structured challenge without overload.
- Task‑specific critical prompts guide constructive critique.
- Measures impact on diversity, calibration, and robustness.

**Talking Points**
- Designed to counter groupthink and disciplinary silos.
- Critique is measured, not just encouraged.
- Improves resilience of conclusions.

**Metrics to Show**
- Diversity: novel positions introduced by advocates / total positions.
- Engagement: composite of reasoning length and critical elements.
- Calibration deltas pre/post critique.

**Example**
- Advocates add alternative legal interpretations → improved calibration and coverage.

---

## Slide Tips (Presenter)

- Use big headers + minimal bullets; keep diagrams central.
- Highlight defaults: `α=0.3, β=0.5, γ=0.2`, `λ=0.95`, `τ=0.4`, `δ>0.6`.
- Timebox: ~45s per pillar; 30s recap if needed.
- End with a single line: “Community‑validated, uncertainty‑aware, meritocratic, transparent.”