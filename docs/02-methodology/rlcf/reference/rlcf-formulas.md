# RLCF — Formule e Definizioni (Riferimento)

Documento di riferimento che illustra in modo preciso e chiaro tutte le formule utilizzate nel framework RLCF, con notazione, variabili, range, valori di default e breve interpretazione operativa.

---

## Notazione Generale

- `u ∈ 𝕌`: utente/valutatore
- `t ∈ ℕ`: tempo discreto (periodi di valutazione)
- `A_u(t)`: autorità dell’utente `u` al tempo `t`
- `B_u`: credenziali di base (baseline credentials)
- `T_u(t)`: track record (storico di performance)
- `P_u(t)`: performance recente (periodo corrente)
- `α, β, γ`: pesi dell’autorità con `α + β + γ = 1`
- `λ`: fattore di decadimento (smoothing) del track record
- `Q_u(t)`: qualità del periodo `t`
- `P`: insieme delle posizioni distinte; `|P|`: numero di posizioni
- `ρ(p)`: probabilità pesata per autorità della posizione `p`
- `δ`: disaccordo normalizzato (entropia)
- `τ`: soglia di incertezza
- `w_j`: pesi della funzione multi‑obiettivo; `O_j`: obiettivi
- `|E|`: numero di valutatori eleggibili per Devil’s Advocate

Valori di default (dalla documentazione): `α=0.3`, `β=0.5`, `γ=0.2`; `λ=0.95` (update factor `1-λ=0.05`); `τ=0.4` (alta incertezza `δ>0.6`).

---

## 1) Autorità Dinamica

Formula principale (autorità)
- `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`

Definizioni e range
- `A_u(t) ∈ [0, 2]`, `B_u ∈ [0, 2]`, `T_u(t), P_u(t) ∈ [0, 1]`
- Pesi: `α, β, γ ∈ [0,1]`, con somma `= 1`

Interpretazione
- Autorità è meritocratica: track record (`β`) e performance recente (`γ`) pesano più di credenziali (`α`).

Esempio
- `B_u=1.2`, `T_u(t-1)=0.7`, `P_u(t)=0.8`, `α=0.3`, `β=0.5`, `γ=0.2` → `A_u(t)=0.3·1.2 + 0.5·0.7 + 0.2·0.8 = 0.36 + 0.35 + 0.16 = 0.87`.

---

## 2) Credenziali di Base (Baseline)

Composizione credenziali
- `B_u = Σ_{i=1}^{n} w_i · f_i(c_{u,i})`

Definizioni
- `w_i ∈ [0,1]` con `Σ w_i = 1`
- `c_{u,i}`: valore grezzo della credenziale per tipo `i`
- `f_i(·)`: funzione di scoring (mappa discreta o formula continua)

Interpretazione
- Le credenziali sono modulari e configurabili; forniscono stabilità iniziale ma non dominano l’autorità totale.

---

## 3) Evoluzione del Track Record

Aggiornamento esponenziale
- `T_u(t) = λ · T_u(t-1) + (1-λ) · Q_u(t)`

Definizioni
- `T_u(t) ∈ [0, 1]`, `λ ≈ 0.95` (default), `Q_u(t) ∈ [0,1]`
- Update factor: `1-λ = 0.05` (peso dell’informazione nuova)

Interpretazione
- Alta inerzia storica (`λ`) con adattamento controllato alla qualità recente.

Esempio
- `T_u(t-1)=0.6`, `Q_u(t)=0.8`, `λ=0.95` → `T_u(t)=0.95·0.6 + 0.05·0.8 = 0.57 + 0.04 = 0.61`.

---

## 4) Qualità del Periodo

Aggregazione qualità
- `Q_u(t) = (1/4) · Σ_{k=1}^{4} q_k`

Componenti (esempi tipici)
- `q_1`: validazione tra pari (media di helpfulness, normalizzata `[0,1]`)
- `q_2`: accuratezza vs. ground truth (`accuracy_score/5`)
- `q_3`: consistenza cross‑task (metrica `[0,1]`)
- `q_4`: valutazione comunitaria (`community_rating/5`)

Interpretazione
- Media semplice di 4 dimensioni di qualità; adattabile alle tipologie di task.

---

## 5) Aggregazione con Preservazione dell’Incertezza

Probabilità pesata per autorità
- `ρ(p) = (Σ_{u: pos(u)=p} A_u(t)) / (Σ_{u ∈ 𝕌} A_u(t))`

Disaccordo normalizzato (entropia)
- `δ = -(1 / log |P|) · Σ_{p ∈ P} ρ(p) · log ρ(p)`

Decisione sull’output
- Se `δ ≤ τ`: output di consenso
- Se `τ < δ ≤ 0.6`: output con incertezza (primario + alternative)
- Se `δ > 0.6`: discussione strutturata (razionali e punti di dissenso)

Interpretazione
- `δ` alto → pluralità di posizioni; il sistema conserva e struttura il dissenso.

Esempio (numerico indicativo)
- `ρ = [0.5, 0.3, 0.2]`, `|P|=3` → `δ ≈ 0.94` (alto) → output con alternative strutturate.

---

## 6) Funzione di Ricompensa Multi‑Obiettivo

Ricompensa comunitaria
- `R_community(x, y) = Σ_{j=1}^{3} w_j · O_j(y)`

Obiettivi e pesi (default)
- Accuratezza `O_1(y) = (F_c + L_r + S_a)/3`, peso `w_1=0.5`
- Utilità `O_2(y) = (P_a + C_o + A_g)/3`, peso `w_2=0.3`
- Trasparenza `O_3(y) = (S_t + R_e + U_d)/3`, peso `w_3=0.2`

Interpretazione
- Ottimizzazione bilanciata fra accuratezza, utilità e trasparenza con pesi configurabili.

---

## 7) Devil’s Advocate — Assegnazione e Metriche

Probabilità di assegnazione
- `P(advocate) = min(0.1, 3/|E|)`

Diversità introdotta
- `Diversity = |Positions_advocates \ Positions_regular| / |Positions_all|`

Engagement (coinvolgimento critico)
- `Engagement = 0.6 · (avg_reasoning_length/50) + 0.4 · (critical_elements/total_feedback)`

Interpretazione
- Assegna un numero contenuto di critici; misura l’apporto di posizioni nuove e la qualità del confronto.

Esempio
- `|E|=50` → `P(advocate)=min(0.1, 3/50)=0.06` (6%).

---

## 8) Metriche di Bias (Sintesi)

Bias totale (composito)
- `B_total = √(Σ b_i²)`

Interpretazione
- Aggregazione quadratica di bias misurati su più dimensioni (ideologico, metodologico, culturale, geografico).

---

## 9) Parametri di Configurazione (Default)

- Pesi autorità: `α=0.3`, `β=0.5`, `γ=0.2` (soggetti a guardrail: `α ≤ 0.6`)
- Smoothing track record: `λ=0.95` (`1-λ=0.05`)
- Soglia di incertezza: `τ=0.4` (alta incertezza: `δ>0.6`)
- Pesi ricompensa: `w_1=0.5`, `w_2=0.3`, `w_3=0.2`

---

## 10) Note Operative

- Tutte le grandezze sono normalizzate ai range indicati per garantire stabilità.
- I pesi sono configurabili a runtime con validazione costituzionale e audit.
- Le formule sono pensate per domini delle scienze sociali; l’adattamento disciplinare avviene tarando pesi e mapping delle credenziali.