# Problem Statement

**Last Updated**: November 2025

---

## The Challenge of Modern Legal Practice

Legal professionals and citizens today face a significant challenge: an **ever-increasing volume of complex, unstructured legal information**. Traditional methods of legal research and analysis are struggling to keep pace with the rapid growth of legislation, case law, and regulatory updates. This information overload leads to several critical problems that hinder the efficiency, accuracy, and accessibility of legal services.

---

## Key Challenges

### 1. Information Overload and Inefficiency

**Problem**: The sheer volume of legal documents makes manual research a time-consuming and labor-intensive process.

**Statistics** (Italian Legal System):
- **450,000+ legislative acts** in force (Normattiva database)
- **100,000+ court decisions** published annually (Cassazione alone)
- **24h lag** for official norm updates in government databases
- **70% of legal research time** spent searching for relevant documents (not analyzing them)

**Impact**:
- High costs for legal services (€200-€500/hour average for lawyer time)
- Delayed justice (months to years for legal research in complex cases)
- Risk of missing relevant precedents or recent legislative changes

**MERL-T Solution**:
- Semantic search with E5-large embeddings (finds relevant docs by meaning, not keywords)
- Multi-source aggregation (5 authoritative sources in single query)
- Real-time Normattiva sync (24h lag for legislative updates)
- **Target**: 70% reduction in research time

---

### 2. Complexity and Ambiguity of Legal Language

**Problem**: Legal texts are characterized by dense jargon, complex sentence structures, and nuanced terminology. This complexity makes it difficult to extract and interpret information accurately, even for experienced legal professionals.

**Examples**:
- Legal definitions that differ from common usage (e.g., "good faith" in contract law)
- Cross-references between norms (e.g., Art. 1425 c.c. references Art. 1442 c.c. for prescription)
- Temporal evolution (same norm text interpreted differently over decades)
- Jurisdictional variations (national law vs. EU directives vs. regional statutes)

**Impact**:
- Misinterpretation risk (especially for non-experts, citizens, small businesses)
- Need for expensive legal consultations even for routine questions
- Barrier to access to justice for economically disadvantaged

**MERL-T Solution**:
- NER (Named Entity Recognition) extracts legal concepts (norms, cases, actors)
- 4 reasoning experts apply different hermeneutic methodologies in parallel:
  - Literal Interpreter: Text-based analysis
  - Systemic-Teleological: Purpose + context
  - Principles Balancer: Constitutional principles (dignity, equality, etc.)
  - Precedent Analyst: Case law interpretation
- Plain language synthesis with provenance (every claim linked to source)
- **Target**: 92%+ factual accuracy (expert validation)

---

### 3. Static and Fragmented Knowledge

**Problem**: Legal knowledge is not static; it evolves with new legislation, court decisions, and interpretations. Traditional legal databases are often fragmented and do not provide a unified, up-to-date view of the law.

**Fragmentation Issues**:
- **Multiple databases**: Normattiva (legislation), Cassazione (case law), university libraries (doctrine)
- **No cross-linking**: Norms don't link to case law, case law doesn't link to academic commentary
- **Temporal gaps**: Old databases don't track norm versions over time
- **Search silos**: Each database has different search interface, no unified query

**Staleness Issues**:
- Normattiva updates daily, but propagation to other systems takes weeks
- Court decisions published with months delay
- Academic commentary years behind current law

**Impact**:
- Incomplete legal analysis (missing relevant sources)
- Risk of relying on outdated information
- Time wasted searching multiple disconnected databases

**MERL-T Solution**:
- **Knowledge Graph**: Unified representation of 5 data sources with cross-links:
  - Normattiva (official legislation)
  - Cassazione (Supreme Court decisions)
  - Dottrina (academic texts)
  - Community (user contributions)
  - RLCF (expert feedback)
- **Temporal Versioning**: Track norm changes over time (e.g., Art. 1425 c.c. version from 1942 vs. 2025)
- **Daily Sync**: Normattiva ingested within 24 hours of official publication
- **Controversy Detection**: Flag conflicts between sources (e.g., Cassazione vs. official text)
- **Target**: 99%+ legal currency (up-to-date information)

---

### 4. Lack of Transparency and Trust in AI

**Problem**: While AI offers a potential solution, many existing legal tech tools are "black boxes." In a domain where explainability and accountability are paramount, the lack of transparency in AI-driven analysis is a significant barrier to adoption.

**Issues with Existing Legal AI**:
- **Hallucination**: LLMs fabricate non-existent norms or case law
- **No provenance**: Claims not linked to authoritative sources
- **Opaque reasoning**: Can't explain why a particular conclusion was reached
- **No uncertainty**: Overconfident answers even when experts disagree
- **Bias**: Models trained on biased data reproduce systemic inequalities

**Examples of Failures**:
- ChatGPT citing non-existent court cases (New York lawyer sanctioned)
- Automated sentencing tools with racial bias (US criminal justice)
- Contract analysis tools missing critical clauses (overconfidence)

**Impact**:
- Legal professionals reluctant to use AI (liability concerns)
- Courts reject AI-assisted briefs (lack of trust)
- Citizens misled by inaccurate AI advice (harm to users)

**MERL-T Solution**:
- **Full Provenance**: Every claim linked to specific norm, case, or doctrine with URN/citation
- **RLCF Framework**: Community validation with transparent authority scoring
- **Uncertainty Preservation**: Disagreement among experts presented, not hidden
- **Explainable Reasoning**: Execution trace shows which experts consulted, sources retrieved
- **Bias Detection**: Built-in module flags demographic disparities (gender, ethnicity, etc.)
- **Human Oversight**: 3 levels (expert review, community validation, model oversight)
- **Target**: 98%+ source attribution, 85%+ expert consensus, full audit trail

---

### 5. High Costs and Accessibility

**Problem**: The high cost of traditional legal research and services limits access to justice. There is a pressing need for more affordable and accessible legal technology solutions.

**Cost Barriers**:
- **Lawyer fees**: €200-€500/hour (average in Italy)
- **Legal databases**: €1,000-€10,000/year subscription (Westlaw, LexisNexis)
- **Expert consultations**: €500-€2,000 for single opinion
- **Court costs**: €1,000-€50,000 for litigation (including lawyer time)

**Accessibility Gaps**:
- **Language**: Legal texts in formal Italian (difficult for non-natives, low-education citizens)
- **Location**: Rural areas lack legal services (lawyers concentrated in cities)
- **Digital divide**: Elderly, low-income citizens can't use complex online databases
- **Discrimination**: Marginalized groups face additional barriers (distrust, cultural norms)

**Impact**:
- **Justice gap**: 80% of low-income citizens can't afford legal services (OECD data)
- **Self-representation**: 30% of civil cases involve unrepresented parties (higher error rate)
- **Legal uncertainty**: Small businesses avoid legal compliance due to costs (risk fines)

**MERL-T Solution**:
- **Free tier**: 100 requests/hour (standard tier) for citizens
- **Open source**: Code, methodology, data (KG) freely available
- **Plain language**: Synthesis in understandable Italian (not legalese)
- **Community support**: 500 expert validators provide free validation (RLCF platform)
- **No-code interface**: Simple web UI (no technical skills required)
- **Multi-channel**: Web, API, mobile (planned)
- **Target**: 10,000 registered users (legal professionals + citizens) by 2027

---

## Why Existing Solutions Fall Short

**Commercial Legal Databases** (Westlaw, LexisNexis, Legge Italia):
- ❌ Expensive subscriptions (€1,000-€10,000/year)
- ❌ Keyword search only (no semantic understanding)
- ❌ No AI reasoning (just document retrieval)
- ❌ Fragmented sources (no cross-database search)
- ✅ Authoritative content (official sources)

**General-Purpose LLMs** (ChatGPT, Claude, Gemini):
- ❌ Hallucination risk (fabricate non-existent law)
- ❌ No provenance (can't verify sources)
- ❌ Generic training (not specialized for Italian law)
- ❌ No community validation (single model, no expert review)
- ✅ Natural language interface (easy to use)

**Legal Tech Startups** (Ross Intelligence, CaseText, etc.):
- ❌ US/UK-centric (limited Italian law coverage)
- ❌ Proprietary (closed source, vendor lock-in)
- ❌ Limited transparency (black-box AI)
- ❌ High cost (subscription models)
- ✅ AI-powered (semantic search, some reasoning)

**MERL-T Unique Advantages**:
- ✅ **Open source** (MIT license for code, CC licenses for data)
- ✅ **Italian law focus** (Normattiva, Cassazione, Italian doctrine)
- ✅ **RLCF validation** (500 expert community, not single model)
- ✅ **Full provenance** (every claim linked to authoritative source)
- ✅ **Transparency** (full execution trace, uncertainty preserved)
- ✅ **Affordable** (free tier + low-cost premium)
- ✅ **EU AI Act compliant** (high-risk system, conformity assessment planned)

---

## The MERL-T Approach

MERL-T addresses these challenges through a unique combination of:

1. **Multi-Source Knowledge Graph**: Unified, cross-linked representation of 5 authoritative sources
2. **Semantic Search**: E5-large embeddings find relevant documents by meaning, not keywords
3. **Multi-Expert Reasoning**: 4 hermeneutic methodologies applied in parallel + synthesizer
4. **RLCF Validation**: Community of 500 legal experts validate outputs, not single model
5. **Full Transparency**: Provenance, execution trace, uncertainty preservation, bias detection
6. **AI Act Compliance**: High-risk system with conformity assessment, GDPR, data protection
7. **Open Source**: Code, methodology, data freely available (non-commercial for KG)

**Result**: Accurate, transparent, affordable, and community-validated legal AI.

---

## Target User Groups

**Primary Users**:
1. **Lawyers** (legal research, case preparation, compliance monitoring)
2. **Judges** (jurisprudence lookup, norm interpretation, case analysis)
3. **Notaries** (contract drafting, property law, succession planning)
4. **In-house counsel** (regulatory compliance, contract review, risk assessment)
5. **Legal scholars** (research, academic publications, teaching)

**Secondary Users**:
6. **Citizens** (understand legal rights, self-help legal information)
7. **Small businesses** (compliance verification, contract templates, employment law)
8. **Public administrators** (regulatory interpretation, procurement law, administrative procedures)
9. **Journalists** (legal context for news stories, fact-checking legal claims)
10. **Students** (legal education, exam preparation, research projects)

**Planned Expansion**:
- **Other EU countries**: Spain, France, Germany (multi-language support)
- **Other domains**: Medical AI, financial compliance (adapt RLCF methodology)

---

## Related Documents

- [Vision](vision.md) - Our vision for democratizing legal knowledge
- [Executive Summary](executive-summary.md) - Project overview and status
- [RLCF Framework](../02-methodology/rlcf/RLCF.md) - Core methodology
- [Architecture](../03-architecture/) - 5-layer system design
- [AI Act Compliance](../05-governance/ai-act-compliance.md) - Regulatory compliance

---

**Document Version**: 2.0 (Expanded)
**Last Updated**: November 2025
**Maintained By**: ALIS Technical Team
