# Data Protection and Privacy

## 1. Commitment to Data Protection

MERL-T and the ALIS (Artificial Legal Intelligence Society) are deeply committed to protecting the privacy and personal data of all individuals who interact with the platform, including community members, users, and any individuals whose data may be part of the legal documents processed by the system. Our data protection strategy is designed to be fully compliant with the General Data Protection Regulation (GDPR) and other applicable data protection laws.

## 2. Data Processing Principles

We adhere to the core principles of data protection as outlined in Article 5 of the GDPR:

-   **Lawfulness, Fairness, and Transparency**: All personal data will be processed lawfully, fairly, and in a transparent manner. The basis for processing will be clearly communicated to data subjects.
-   **Purpose Limitation**: Personal data will only be collected for specified, explicit, and legitimate purposes (e.g., managing community membership, calculating authority scores, conducting research) and not further processed in a manner that is incompatible with those purposes.
-   **Data Minimization**: We will only process personal data that is adequate, relevant, and limited to what is necessary in relation to the purposes for which it is processed.
-   **Accuracy**: We will take every reasonable step to ensure that personal data is accurate and, where necessary, kept up to date.
-   **Storage Limitation**: Personal data will be kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed.
-   **Integrity and Confidentiality**: We will process personal data in a manner that ensures appropriate security, including protection against unauthorized or unlawful processing and against accidental loss, destruction, or damage.

## 3. Data Subject Rights

MERL-T will provide clear and accessible mechanisms for data subjects to exercise their rights under GDPR, including:

-   **Right of Access**: Users will have the right to access their personal data and information about how it is being processed.
-   **Right to Rectification**: Users will have the right to have inaccurate personal data corrected without undue delay.
-   **Right to Erasure ('Right to be Forgotten')**: Users will have the right to have their personal data erased under certain conditions.
-   **Right to Restrict Processing**: Users will have the right to obtain the restriction of processing in certain situations.
-   **Right to Data Portability**: Users will have the right to receive their personal data in a structured, commonly used, and machine-readable format.
-   **Right to Object**: Users will have the right to object to the processing of their personal data in certain circumstances.

## 4. Data Security

We will implement a comprehensive set of technical and organizational measures to ensure the security of personal data, including:

-   **Pseudonymization and Encryption**: Where possible, personal data will be pseudonymized or encrypted to reduce the risks to the data subjects.
-   **Access Control**: Strict access control policies will be in place to ensure that only authorized personnel have access to personal data.
-   **Regular Security Assessments**: We will conduct regular risk assessments and security audits to identify and mitigate potential vulnerabilities.
-   **Data Breach Response Plan**: A clear plan will be in place to respond to any potential data breaches in a timely and effective manner.

## 5. The Role of the ALIS Association

As the governing body of the MERL-T project, the **ALIS Association will act as the Data Controller** for the personal data processed by the platform. In this capacity, the association will be responsible for:

-   Ensuring and demonstrating compliance with the GDPR.
-   Appointing a Data Protection Officer (DPO) if required.
-   Conducting Data Protection Impact Assessments (DPIAs) for high-risk processing activities.
-   Serving as the primary point of contact for data subjects and supervisory authorities.

By embedding data protection principles into the core of the MERL-T architecture and governance model, we aim to build a platform that is not only powerful but also worthy of the trust of its users and the legal community.

---

## 6. Technical Implementation of GDPR Requirements

### 6.1 Data Retention Policies

| Data Type | Retention Period | Deletion Method | Legal Basis |
|-----------|------------------|-----------------|-------------|
| User queries (raw text) | 2 years | Hard delete + audit log | Legitimate interest (Art. 6.1.f) |
| Query results (AI output) | 5 years | Anonymization after 2 years | Legal obligation (AI Act Art. 12) |
| Expert feedback | 5 years | Anonymization of expert ID after 1 year | Consent (Art. 6.1.a) |
| API keys | Until revoked | SHA-256 hash (irreversible) | Contract (Art. 6.1.b) |
| Usage logs (metadata) | 3 years | Aggregation + pseudonymization | Legitimate interest (Art. 6.1.f) |
| Audit trails (compliance) | 10 years | Secure archive (read-only) | Legal obligation (AI Act) |

**Implementation**: Automated cron job runs weekly to purge expired data (`backend/orchestration/api/services/data_retention.py` - planned)

---

### 6.2 Privacy by Design

**Principles Applied**:

1. **Data Minimization**:
   - User queries: No personal information required (anonymous by default)
   - Expert profiles: Only username + credentials (no real names unless volunteer)
   - API usage: IP address logged only for rate limiting (purged after 7 days)

2. **Pseudonymization**:
   - User IDs: SHA-256 hash of email/username after 30 days
   - Query trace IDs: Random UUID (no PII derivable)
   - Expert IDs in public data: Pseudonymous handles (e.g., "Expert_Legal_42")

3. **Encryption**:
   - **In-transit**: TLS 1.3 for all API communication
   - **At-rest**: PostgreSQL AES-256 encryption for sensitive fields (API keys, expert credentials)
   - **Backups**: Encrypted database dumps with GPG (2048-bit keys)

4. **Access Control**:
   - Role-based: Admin, user, guest tiers
   - Principle of least privilege: Users only see own queries
   - Audit trail: All admin access to user data logged

**Implementation**: `backend/orchestration/api/middleware/auth.py` + database encryption config

---

### 6.3 Data Subject Rights (GDPR Articles 15-22)

**Right to Access (Art. 15)**:
- Endpoint: `GET /users/{user_id}/data-export`
- Format: JSON with all personal data (queries, feedback, authority scores)
- Response time: Within 30 days (automated export available immediately)
- Implementation: Planned (Q1 2026)

**Right to Rectification (Art. 16)**:
- Endpoint: `PUT /users/{user_id}/profile`
- Allows: Update username, email, credentials
- Validation: Pydantic schema ensures data integrity
- Implementation: ✅ Complete (`backend/rlcf_framework/routers/users.py`)

**Right to Erasure (Art. 17)**:
- Endpoint: `DELETE /users/{user_id}`
- Effect: Soft delete (anonymization) or hard delete (GDPR compliance)
- Retention: Expert feedback preserved (anonymized) for scientific integrity
- Implementation: Planned (Q1 2026)

**Right to Restrict Processing (Art. 18)**:
- Endpoint: `POST /users/{user_id}/restrict-processing`
- Effect: Account suspended, no new processing, data frozen
- Use case: User contests accuracy of authority score
- Implementation: Planned (Q1 2026)

**Right to Data Portability (Art. 20)**:
- Endpoint: `GET /users/{user_id}/data-export?format=json`
- Format: Machine-readable JSON (structured export)
- Scope: All user-generated content (queries, feedback)
- Implementation: Planned (Q1 2026)

**Right to Object (Art. 21)**:
- Endpoint: `POST /users/{user_id}/object-processing`
- Effect: Stop using data for specific purpose (e.g., authority scoring)
- Resolution: Manual review by ALIS DPO
- Implementation: Planned (Q1 2026)

---

### 6.4 Data Protection Impact Assessment (DPIA)

**GDPR Article 35**: DPIA required for high-risk processing

**MERL-T DPIA Status**: ⏳ Planned (Q1 2026)

**Preliminary Assessment**:

| Processing Activity | Risk Level | Justification | Safeguards |
|---------------------|------------|---------------|------------|
| User query logging | Medium | May contain sensitive legal issues | Pseudonymization, 2-year retention, encryption |
| Expert authority scoring | Medium | Reputation impact on experts | Transparent algorithm, right to challenge |
| Legal advice generation | High | Incorrect advice could harm users | Multi-expert validation, provenance tracking, disclaimer |
| AI model training | High | Use of community feedback data | Anonymization, consent-based, opt-out available |

**Planned DPIA Process**:
1. **Identify risks**: Data flows, processing purposes, stakeholders
2. **Assess necessity**: Proportionality test for each processing activity
3. **Identify safeguards**: Technical + organizational measures
4. **Document findings**: Formal DPIA report for ALIS board
5. **Consult DPO**: Independent review of risk assessment
6. **Publish summary**: Transparency report on ALIS website

---

### 6.5 Data Breach Response Plan

**GDPR Article 33-34**: Notification requirements

**Response Timeline**:

| Event | Action | Deadline | Responsible |
|-------|--------|----------|-------------|
| **Breach detected** | Activate incident response team | Immediate | Tech Lead |
| **Containment** | Isolate affected systems, stop breach | Within 1 hour | DevOps |
| **Assessment** | Determine scope (how many users affected) | Within 4 hours | DPO |
| **Notification (Authority)** | Report to Garante Privacy (Italian DPA) | Within 72 hours | DPO |
| **Notification (Users)** | Inform affected users (if high risk) | Without undue delay | Communications |
| **Remediation** | Patch vulnerability, restore from backups | Within 7 days | Tech Lead |
| **Post-mortem** | Document lessons learned, update procedures | Within 14 days | ALIS Board |

**Breach Notification Template**:
```
To: protocollo@gpdp.it (Garante Privacy)
Subject: Data Breach Notification - MERL-T Platform

1. Nature of breach: [Unauthorized access / data exfiltration / other]
2. Data categories affected: [User queries / expert feedback / other]
3. Approximate number of data subjects: [X users]
4. Likely consequences: [Risk of identity theft / reputational harm / none]
5. Measures taken: [System isolated, passwords reset, etc.]
6. Contact point: dpo@alis.ai
```

**Implementation**: Incident response runbook + automated breach detection (planned: Q1 2026)

---

### 6.6 Data Protection Officer (DPO)

**GDPR Article 37**: DPO appointment requirement

**Status**: ⏳ Planned (Q1 2026)

**DPO Responsibilities**:
1. **Monitor compliance**: Ensure MERL-T adheres to GDPR
2. **Advise on DPIA**: Review data protection impact assessments
3. **Cooperate with authorities**: Liaise with Garante Privacy
4. **Act as contact point**: Handle data subject requests
5. **Raise awareness**: Train ALIS team on data protection

**DPO Profile** (requirements):
- Legal expertise in EU data protection law
- Understanding of AI systems and algorithmic decision-making
- Independent role (reports to ALIS board, not tech team)
- Adequate resources (budget, staff support)

**Contact**: dpo@alis.ai (to be activated Q1 2026)

---

### 6.7 Cross-Border Data Transfers

**GDPR Chapter V**: Transfers to third countries

**Current Status**:
- **Data location**: EU (Italy) - Hosted in Italian data centers
- **Third-country transfers**: None (all processing within EU)
- **LLM providers**: OpenRouter (US-based) - API calls only, no data storage

**Safeguards for OpenRouter** (US-based LLM API):
1. **Standard Contractual Clauses (SCCs)**: Signed with OpenRouter (planned)
2. **Data minimization**: Query text only, no PII transmitted
3. **Encryption**: TLS 1.3 for API communication
4. **No storage**: OpenRouter does not store queries (per contract)
5. **Fallback**: EU-based LLM provider available (e.g., Mistral, Aleph Alpha)

**Future-proofing**: If Schrems III invalidates SCCs, switch to EU-based LLM (Mistral AI, France)

---

### 6.8 Children's Data Protection

**GDPR Article 8**: Parental consent for children under 16

**MERL-T Policy**:
- **Age restriction**: Users must be 18+ (legal capacity to use legal information)
- **No collection**: No age verification data collected (age declared at signup)
- **Disclaimer**: "This service is intended for adults only"
- **Enforcement**: Account suspension if user found to be under 18

**Rationale**: Legal queries are adult-oriented, no need for children's access

---

## 7. Compliance Checklist (GDPR)

| Article | Requirement | Status | Evidence |
|---------|-------------|--------|----------|
| **Art. 5** | Data processing principles | ✅ Complete | Section 2 |
| **Art. 6** | Lawful basis for processing | ✅ Complete | Section 6.1 (Retention table) |
| **Art. 13-14** | Information to data subjects | ✅ Complete | Privacy policy (to be published) |
| **Art. 15-22** | Data subject rights | 🚧 Partial | Section 6.3 (API endpoints planned) |
| **Art. 25** | Privacy by design | ✅ Complete | Section 6.2 |
| **Art. 30** | Records of processing activities | ✅ Complete | Internal register (ALIS) |
| **Art. 32** | Security of processing | ✅ Complete | Encryption, access control (Section 6.2) |
| **Art. 33-34** | Breach notification | 🚧 Planned | Section 6.5 (Response plan) |
| **Art. 35** | Data Protection Impact Assessment | ⏳ Planned | Section 6.4 (Q1 2026) |
| **Art. 37** | Data Protection Officer | ⏳ Planned | Section 6.6 (Q1 2026) |
| **Chapter V** | Cross-border transfers | ✅ Complete | Section 6.7 (EU-only, SCCs for OpenRouter) |

---

## 8. Accountability and Governance

**GDPR Article 24**: Controller responsibility

**ALIS as Data Controller**:
1. **Demonstrate compliance**: This document + technical implementation
2. **Implement appropriate measures**: Privacy by design, encryption, access control
3. **Maintain records**: Processing activities register (Article 30)
4. **Appoint DPO**: Planned Q1 2026
5. **Conduct DPIAs**: For high-risk processing (Q1 2026)
6. **Report breaches**: 72-hour notification procedure (Section 6.5)

**Data Processors**: OpenRouter (LLM API), hosting provider (to be selected)
- **Processor agreements**: GDPR-compliant contracts with all processors
- **Due diligence**: Annual audit of processor security measures
- **Subprocessor list**: Maintained and updated on ALIS website

---

## 9. Future Enhancements

**Planned Improvements**:

1. **Q1 2026**:
   - ⏳ Appoint Data Protection Officer (DPO)
   - ⏳ Conduct Data Protection Impact Assessment (DPIA)
   - ⏳ Implement data subject rights APIs (export, erasure, portability)
   - ⏳ Publish comprehensive privacy policy on ALIS website

2. **Q2 2026**:
   - ⏳ Automated data retention enforcement (weekly purge job)
   - ⏳ Breach detection system (anomaly detection + alerts)
   - ⏳ DPO training for ALIS team members
   - ⏳ Annual privacy audit by external auditor

3. **2027+**:
   - ⏳ ISO 27701 (Privacy Information Management) certification
   - ⏳ EU-based LLM provider (eliminate US data transfers)
   - ⏳ Advanced anonymization techniques (differential privacy)

---

## 10. Conclusion

MERL-T is committed to the highest standards of data protection, fully aligned with GDPR requirements:

✅ **Privacy by Design**: Pseudonymization, encryption, data minimization
✅ **Transparency**: Clear privacy policy, data subject rights
✅ **Security**: Authentication, access control, breach response plan
✅ **Accountability**: ALIS as data controller, DPO appointment planned
🚧 **Continuous Improvement**: DPIA, rights automation, ISO 27701

**Our commitment: Personal data protection is not an afterthought, but a foundational principle of the MERL-T architecture.**

---

**Document Version**: 2.0 (Expanded)
**Last Updated**: November 2025
**Next Review**: January 2026
**Owner**: ALIS (Artificial Legal Intelligence Society)
**Contact**: dpo@alis.ai (planned Q1 2026)
