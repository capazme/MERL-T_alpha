# Vision

**Last Updated**: November 2025

---

## Democratizing Legal Knowledge through Principled AI

Our vision is to create a world where **legal knowledge is no longer a barrier, but a tool for empowerment**. We envision a future where MERL-T, powered by the innovative **Reinforcement Learning from Community Feedback (RLCF)** framework, acts as an intelligent partner for legal professionals and citizens alike—automating mundane tasks, revealing hidden insights, and enabling a deeper, more nuanced understanding of the law.

---

## Core Principles of Our Vision

### 1. Augmented Intelligence, Not Replacement

**Principle**: We believe in augmenting, not replacing, human expertise.

**How MERL-T Implements This**:
- **4 Expert Perspectives**: Literal, Systemic-Teleological, Principles, Precedent (not single "correct" answer)
- **Uncertainty Preservation**: Disagreement among experts presented as valuable information
- **Human-in-the-Loop**: 500 expert community validates outputs (RLCF framework)
- **Authority Scoring**: Expertise earned through demonstrated competence, not static credentials

**Vision for the Future**:
- Lawyers use MERL-T to **explore multiple interpretations** of ambiguous norms
- Judges reference MERL-T for **comprehensive jurisprudence review** (not just keyword search)
- Citizens understand **different legal perspectives** on their situation (not oversimplified advice)

**Not**: AI making final legal decisions
**Instead**: AI providing **tools for better human decision-making**

---

### 2. Radical Accessibility

**Principle**: We aim to break down the barriers to accessing legal information.

**Current Reality**:
- €1,000-€10,000/year for professional legal databases
- €200-€500/hour for lawyer consultations
- 80% of low-income citizens can't afford legal services (OECD)
- Legal texts in dense jargon (inaccessible to non-experts)

**MERL-T's Approach**:
- **Free Tier**: 100 requests/hour for citizens (standard tier)
- **Open Source**: Code (MIT), methodology (CC BY-SA), KG data (CC BY-NC-SA)
- **Plain Language**: Synthesis in understandable Italian (not legalese)
- **No Technical Barrier**: Simple web UI (no coding required)
- **Multi-Channel**: Web, API, mobile (planned)

**Vision for the Future**:
- **10,000 users** (legal professionals + citizens) by 2027
- **Zero-cost legal research** for non-commercial use
- **Multilingual support** (Italian, English, French, German) by 2028
- **Voice interface** for accessibility (visually impaired, elderly)

**Impact**:
- Reduce justice gap from 80% to 50% of underserved population
- Enable self-representation in simple cases (reduced court burden)
- Empower citizens to know their rights (preventive legal knowledge)

---

### 3. Transparency and Trust through RLCF

**Principle**: We are committed to building a transparent and trustworthy AI.

**The RLCF Framework** (4 Pillars):

#### **Pillar 1: Dynamic Authority**
- **Principle**: True expertise is earned and demonstrated over time, not static credentials.
- **Implementation**: Authority score `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`
  - Base authority (credentials)
  - Temporal authority (recent accuracy)
  - Performance (task success)
- **Result**: Experts who provide accurate feedback gain influence; poor performers lose authority

#### **Pillar 2: Preserved Uncertainty**
- **Principle**: Expert disagreement is valuable information, not noise.
- **Implementation**: Shannon entropy quantifies disagreement; consensus level displayed (0-1 scale)
- **Result**: Users see 85% expert agreement + alternative viewpoints (15% disagreement)
- **Contrast**: Traditional AI forces single answer even when experts disagree

#### **Pillar 3: Transparent Process**
- **Principle**: Every step of validation must be auditable and reproducible.
- **Implementation**:
  - Full execution trace (preprocessing → routing → retrieval → reasoning → synthesis)
  - Provenance for every claim (norm ID, case ID, doctrine citation)
  - Expert opinions visible (which experts consulted, their reasoning)
  - Authority scores public (not hidden black-box weights)
- **Result**: Users can verify AI reasoning step-by-step

#### **Pillar 4: Universal Expertise**
- **Principle**: Value cross-domain insights; expertise emerges organically.
- **Implementation**:
  - Legal professionals + academics + technologists in ALIS community
  - No gatekeeping (anyone can join, authority earned through contributions)
  - Cross-pollination (tech experts flag AI bias, legal experts validate norms)
- **Result**: Richer, more diverse validation (not just legal insiders)

**Vision for the Future**:
- **500 active experts** validating 1,000 queries/month (2-year goal)
- **Public RLCF dashboard** showing authority scores, disagreement patterns, controversy topics
- **Peer-reviewed publications** on RLCF methodology (academic credibility)
- **Standard for legal AI** (other systems adopt RLCF principles)

---

### 4. A Living Legal System

**Principle**: We see the law not as a static collection of documents, but as a dynamic, interconnected system.

**The Knowledge Graph Approach**:

**Nodes** (Entities):
- Norms (legislative acts, articles, paragraphs)
- Cases (court decisions, precedents)
- Concepts (legal principles, doctrinal theories)
- Actors (legislators, judges, scholars)

**Edges** (Relationships):
- CITES (norm cites another norm)
- INTERPRETS (case interprets norm)
- MODIFIES (new norm amends old norm)
- CONTRADICTS (sources in conflict)
- SUPPORTS (doctrine supports case law)

**Temporal Dimension**:
- Version tracking (e.g., Art. 1425 c.c. from 1942 vs. 2025)
- Precedent evolution (early cases vs. modern interpretation)
- Legislative intent (historical context, parliamentary debates)

**Vision for the Future**:
- **Live updates**: Normattiva sync within 1 hour (currently 24h)
- **Predictive analytics**: Detect emerging legal trends (e.g., new interpretations of data protection)
- **Impact analysis**: Trace effects of new legislation through entire legal system
- **Cross-jurisdictional**: EU law + national law + regional statutes in single graph

**Impact**:
- Lawyers see **full context** of norms (not isolated articles)
- Scholars map **legal evolution** over decades (not snapshots)
- Citizens understand **why law changed** (democratic transparency)

---

### 5. Collaborative Innovation

**Principle**: We believe in the power of community.

**The ALIS Association**:
- **Legal Form**: Non-profit association (Italy)
- **Governance**: Democratic (General Assembly elects Board)
- **Membership**: 500 target (legal professionals, academics, technologists, citizens)
- **IP Model**: Open source (MIT for code, CC licenses for data/methodology)

**Community-Driven Development**:

**Feedback Loops**:
1. **RLCF Platform**: Experts validate query results weekly
2. **GitHub Issues**: Public bug reports + feature requests
3. **Annual Conference**: In-person collaboration (presentations, workshops, networking)
4. **Online Forum**: Async discussions (legal AI ethics, methodology, use cases)

**Incentives**:
- **Top 10 authority scores**: "RLCF Fellow" badge + free premium API (1 year)
- **100+ feedback submissions**: "Community Pillar" status + conference invitation
- **Research contributions**: Co-authorship on publications + data access
- **Honorary membership**: Exceptional contributors (voting rights, no fees)

**Vision for the Future**:
- **ALIS chapters** in other EU countries (Spain, France, Germany) by 2028
- **1,000 members** (global legal AI community) by 2029
- **Standards body**: ALIS influences EU AI Act implementation guidelines
- **Open-source ecosystem**: Derivative projects for medical AI, financial compliance (adapt RLCF)

---

## Long-Term Vision (2030+)

### Technical Vision

**System Capabilities**:
- **Multi-language**: Italian, English, French, German, Spanish (EU coverage)
- **Multi-domain**: Legal + medical + financial (RLCF methodology adapted)
- **Real-time**: <1 second latency (current: ~5 seconds)
- **Accuracy**: 98%+ (current: 92%)
- **Scale**: 1 million queries/month (current: pre-launch)

**AI Advancements**:
- **Fine-tuned LLMs**: Italian-legal-BERT (self-hosted, no OpenRouter dependency)
- **Automated fact-checking**: Cross-reference all claims with KG (no hallucination)
- **Adaptive routing**: Router learns optimal expert combinations per query type
- **Continuous learning**: Weekly model updates from RLCF feedback (currently manual)

### Social Vision

**Impact on Legal Profession**:
- **70% time savings** in legal research (target achieved)
- **50% cost reduction** for legal services (pass savings to clients)
- **New roles**: "Legal AI auditors" (validate AI outputs for courts)
- **Upskilling**: Lawyers become "AI-augmented experts" (not replaced)

**Impact on Access to Justice**:
- **50% reduction** in justice gap (from 80% to 40% underserved)
- **Free legal information** for 100,000 citizens/month
- **Self-representation toolkit**: Templates, checklists, explainers (AI-generated)
- **Rural access**: Legal services via internet (no geographic barrier)

**Impact on Rule of Law**:
- **Transparency**: Citizens understand law (not just legal elites)
- **Consistency**: AI reduces arbitrary interpretation (bias detection)
- **Democracy**: Participate in legal discourse (RLCF community open to all)
- **EU leadership**: MERL-T as model for ethical, compliant legal AI

### Governance Vision

**ALIS as Institution**:
- **Legal recognition**: Consultative status at EU AI Office (influence policy)
- **Academic standing**: University partnerships (research grants, PhDs)
- **Financial sustainability**: €500,000/year budget (membership + commercial API + grants)
- **Global reach**: 1,000 members from 50+ countries

**RLCF as Standard**:
- **Other domains adopt**: Medical AI, financial compliance, scientific research
- **Academic citations**: 100+ papers reference RLCF methodology
- **ISO standard**: RLCF formalized as international standard for AI alignment (like ISO 9001 for quality)
- **Textbook inclusion**: University courses teach RLCF as alternative to RLHF

---

## Why This Vision Matters

**For Democracy**:
- **Informed citizenship**: Legal knowledge empowers democratic participation
- **Accountability**: Transparent AI enables oversight (not opaque algorithms)
- **Equal access**: Justice not limited to wealthy elite

**For Innovation**:
- **Open source**: Accelerates progress (not proprietary silos)
- **Community-driven**: Diverse perspectives → better solutions
- **Academic rigor**: Peer review → trustworthy methodology

**For Europe**:
- **AI Act compliance**: MERL-T demonstrates high-risk system can be ethical
- **Digital sovereignty**: EU-based legal AI (not US Big Tech dependency)
- **Multilingual**: Respects linguistic diversity (not English-only)

**For Humanity**:
- **Principled AI**: RLCF model for alignment (not just legal domain)
- **Human dignity**: AI augments, not replaces, human expertise
- **Global good**: Methodology transferable to Global South (medical, education)

---

## Join Our Vision

**We invite you to join us** in building the future of ethical legal AI:

**For Legal Professionals**:
- Become an RLCF expert (validate queries, earn authority)
- Join ALIS association (€100/year expert membership)
- Shape the platform (propose features, vote on roadmap)

**For Researchers**:
- Access KG data (for academic research)
- Co-author publications (RLCF methodology, legal AI ethics)
- Supervise PhDs (ALIS partners with universities)

**For Technologists**:
- Contribute code (GitHub, MIT license)
- Improve infrastructure (database optimization, API performance)
- Build integrations (mobile app, voice interface, IDE plugins)

**For Citizens**:
- Use the platform (free tier, no registration required)
- Provide feedback (report errors, suggest improvements)
- Support ALIS (€25/year supporting membership)

**Contact**: info@alis.ai | Website: alis.ai (planned)

---

## Related Documents

- [Problem Statement](problem-statement.md) - Challenges MERL-T addresses
- [Executive Summary](executive-summary.md) - Project overview and current status
- [RLCF Framework](../02-methodology/rlcf/RLCF.md) - Core methodology (theoretical paper)
- [AI Act Compliance](../05-governance/ai-act-compliance.md) - Regulatory compliance strategy
- [ALIS Association](../05-governance/arial-association.md) - Community governance

---

**Document Version**: 2.0 (Expanded)
**Last Updated**: November 2025
**Maintained By**: ALIS Technical Team

---

> **"The law belongs to the people, not to the experts. MERL-T is our tool to return legal knowledge to its rightful owners."**
> — ALIS Vision Statement
