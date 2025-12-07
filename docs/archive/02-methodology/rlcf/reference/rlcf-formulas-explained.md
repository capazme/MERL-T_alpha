# RLCF Formulas Explained for a General Audience

This document translates the mathematical framework of RLCF into clear, accessible concepts for professionals from diverse backgrounds, including law, economics, and other social sciences. Each formula is presented with its intuitive goal, an analogy, a breakdown of its components, and a practical example.

---

## 1. Dynamic Authority Score (`A_u(t)`)

### Intuitive Goal
This formula answers the question: **"How much should we trust this contributor's feedback right now?"** It calculates a contributor's authority score, ensuring that expertise is not static but earned and proven over time. It balances a person's background with their actual, demonstrated performance.

### Analogy
Think of it as a **dynamic professional reputation score**. A lawyer's reputation isn't just based on their law school degree (credentials). It's a mix of their long-term track record in winning cases (historical performance) and how well they've handled their most recent, high-profile case (recent performance).

### The Formula
$$
A_u(t) = \alpha \cdot B_u + \beta \cdot T_u(t-1) + \gamma \cdot P_u(t)
$$

### Breakdown of Variables

| Variable | Name | What It Means | Why It's Important |
| :--- | :--- | :--- | :--- |
| **`A_u(t)`** | **Authority Score** | The final, calculated authority of contributor `u` at time `t`. | This score determines the weight of their feedback in the system. |
| **`B_u`** | **Baseline Credentials** | The contributor's static, background qualifications (e.g., degrees, years of experience). | Provides a stable, foundational measure of expertise. |
| **`T_u(t-1)`** | **Track Record** | The contributor's historical performance, based on the quality of their past feedback. | Rewards consistent, high-quality contributions over the long term. |
| **`P_u(t)`** | **Recent Performance** | The quality of the contributor's work in the most recent evaluation period. | Allows the system to quickly recognize emerging experts or flag declining performance. |
| **`α, β, γ`** | **Weights** | Configurable parameters that determine the influence of each component. | They allow us to tune the system. For law, we might weigh track record (`β`) heavily, as sustained performance is key. |

### Practical Example (Legal Context)
- **Contributor**: A seasoned judge.
- **`B_u` (Credentials)**: High score due to a PhD in Law and 20 years on the bench.
- **`T_u(t-1)` (Track Record)**: Very high score because their past legal analyses submitted to the system have been consistently rated as insightful and accurate by peers.
- **`P_u(t)` (Recent Performance)**: A slightly lower score because their most recent feedback on a complex AI-generated contract was flagged as missing a subtle but critical new precedent.
- **Result**: The judge's final **Authority Score `A_u(t)`** remains high due to their strong credentials and track record, but the dip in recent performance slightly tempers it, reflecting the need to stay current.

---

## 2. Disagreement Score (`δ`)

### Intuitive Goal
This formula answers the question: **"Are the experts agreeing or disagreeing on this topic?"** It measures the level of consensus or dissent among contributors, weighted by their authority.

### Analogy
Think of it as an **"Expert Opinion Poll."** If all trusted experts vote the same way, disagreement is low. If they are split into multiple, well-supported camps, disagreement is high. The formula doesn't just count votes; it gives more weight to the "votes" of experts with a better reputation (higher authority).

### The Formula
$$
\delta = -\frac{1}{\log|P|} \sum_{p \in P} \rho(p) \log \rho(p)
$$

### Breakdown of Variables

| Variable | Name | What It Means | Why It's Important |
| :--- | :--- | :--- | :--- |
| **`δ`** | **Disagreement Score** | The final score from 0 (total agreement) to 1 (maximum disagreement). | It tells the system whether to provide a single consensus answer or to report on the different expert viewpoints. |
| **`P`** | **Set of Positions** | The different answers or viewpoints submitted by the contributors. | Represents the "camps" of opinion. |
| **`ρ(p)`** | **Weighted Support** | The proportion of total authority supporting a specific position `p`. | This is the "weighted vote count" for each opinion. |

### Practical Example (Legal Context)
- **Task**: An AI model analyzes a contract clause and deems it "unenforceable."
- **Scenario 1: Low Disagreement (`δ` ≈ 0.1)**
    - Ten legal experts review it. Nine, all with high authority, agree it's "unenforceable." One junior analyst disagrees.
    - The **Weighted Support `ρ(p)`** for "unenforceable" is massive.
    - **Result**: The system confidently outputs "The clause is likely unenforceable" because there is a strong consensus.
- **Scenario 2: High Disagreement (`δ` ≈ 0.7)**
    - Ten experts review it. Five high-authority commercial lawyers say it's "enforceable." Five high-authority consumer rights lawyers say it's "unenforceable," citing a new regulation.
    - The **Weighted Support `ρ(p)`** is split almost 50/50 between the two positions.
    - **Result**: The system detects high, meaningful disagreement. Instead of picking a side, it outputs:
        - **Primary Position**: "This clause may be unenforceable."
        - **Alternative View**: "However, there is a strong, competing expert view that it is enforceable, particularly from a commercial law perspective. The key point of contention is the interpretation of [New Regulation]."

---

## 3. Track Record Evolution (`T_u(t)`)

### Intuitive Goal
This formula answers: **"Is this contributor's performance getting better or worse over time?"** It updates a contributor's long-term track record by blending their past performance with their most recent quality score.

### Analogy
Think of it as an **Exponentially Smoothed Average of performance reviews**. It's like a GPA that gives slightly more weight to your most recent semester's grades but still heavily reflects your overall academic history. A single bad day won't ruin a great reputation, but a consistent decline will gradually lower it.

### The Formula
$$
T_u(t) = \lambda \cdot T_u(t-1) + (1-\lambda) \cdot Q_u(t)
$$

### Breakdown of Variables

| Variable | Name | What It Means | Why It's Important |
| :--- | :--- | :--- | :--- |
| **`T_u(t)`** | **New Track Record** | The updated track record score. | Keeps the contributor's reputation current. |
| **`T_u(t-1)`** | **Old Track Record** | The score from the previous period. | Represents historical stability. |
| **`Q_u(t)`** | **Recent Quality Score** | A combined score reflecting the quality of recent feedback (accuracy, helpfulness, etc.). | Injects new performance data into the long-term record. |
| **`λ`** | **Decay/Smoothing Factor** | A number close to 1 (e.g., 0.95). It determines how much weight is kept on the old track record. | A high `λ` ensures stability and prevents wild swings in reputation based on a single piece of feedback. |

### Practical Example (Legal Context)
- **Contributor**: A promising young lawyer.
- **`T_u(t-1)` (Old Track Record)**: 0.70 (Good, but not top-tier).
- **`Q_u(t)` (Recent Quality)**: 0.95. They submitted an exceptionally well-researched analysis of a complex case, which was highly praised by senior partners.
- **`λ`**: 0.95 (standard value).
- **Calculation**:
    - `New Score = (0.95 * 0.70) + (0.05 * 0.95)`
    - `New Score = 0.665 + 0.0475 = 0.7125`
- **Result**: Their **New Track Record `T_u(t)`** increases from 0.70 to 0.7125. The improvement is gradual, not dramatic, because the system values long-term consistency. However, if they keep performing at this high level, their score will steadily climb towards the top.