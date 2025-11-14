"""
OpenAPI Examples for Request/Response Schemas

This module provides comprehensive examples for all API endpoints with
multiple scenarios to help users understand different use cases.

These examples are used in OpenAPI schema generation to populate
Swagger UI with realistic, diverse examples.

Author: Week 9 Day 2
Date: November 2025
"""

# ============================================================================
# QUERY REQUEST EXAMPLES
# ============================================================================

QUERY_REQUEST_EXAMPLES = {
    "simple_contract_question": {
        "summary": "Simple Contract Question",
        "description": "Basic legal question about contract validity",
        "value": {
            "query": "È valido un contratto firmato da un sedicenne?",
            "session_id": None,
            "context": {
                "temporal_reference": "latest",
                "jurisdiction": "nazionale",
                "user_role": "cittadino"
            },
            "options": {
                "max_iterations": 3,
                "return_trace": True
            }
        }
    },
    "citizenship_requirements": {
        "summary": "Citizenship Requirements",
        "description": "Research query about Italian citizenship",
        "value": {
            "query": "Quali sono i requisiti per ottenere la cittadinanza italiana per matrimonio?",
            "session_id": "session_abc123",
            "context": {
                "temporal_reference": "latest",
                "jurisdiction": "nazionale",
                "user_role": "cittadino"
            },
            "options": {
                "max_iterations": 2,
                "return_trace": False
            }
        }
    },
    "gdpr_compliance": {
        "summary": "GDPR Compliance Check",
        "description": "Compliance verification question",
        "value": {
            "query": "Il mio sito web rispetta i requisiti del GDPR per il trattamento dei dati personali?",
            "session_id": "compliance_check_001",
            "context": {
                "temporal_reference": "latest",
                "jurisdiction": "comunitario",
                "user_role": "avvocato"
            },
            "options": {
                "max_iterations": 3,
                "return_trace": True
            }
        }
    },
    "jurisprudence_lookup": {
        "summary": "Jurisprudence Lookup",
        "description": "Search for relevant case law",
        "value": {
            "query": "Quali sentenze della Cassazione riguardano l'articolo 1372 del Codice Civile sulla responsabilità contrattuale?",
            "session_id": None,
            "context": {
                "temporal_reference": "2020-01-01",
                "jurisdiction": "nazionale",
                "user_role": "avvocato"
            },
            "options": {
                "max_iterations": 3,
                "return_trace": True
            }
        }
    },
    "multi_turn_conversation": {
        "summary": "Multi-turn Conversation",
        "description": "Follow-up question in ongoing conversation",
        "value": {
            "query": "E se invece il contratto fosse stato firmato da un diciassettenne?",
            "session_id": "conv_xyz789",
            "context": {
                "temporal_reference": "latest",
                "jurisdiction": "nazionale",
                "user_role": "studente",
                "previous_queries": [
                    "È valido un contratto firmato da un sedicenne?"
                ]
            },
            "options": {
                "max_iterations": 2,
                "return_trace": False
            }
        }
    }
}

# ============================================================================
# QUERY RESPONSE EXAMPLES
# ============================================================================

QUERY_RESPONSE_EXAMPLES = {
    "successful_answer": {
        "summary": "Successful Answer",
        "description": "Complete answer with high confidence",
        "value": {
            "trace_id": "QRY-20251115123045-abc123",
            "query": "È valido un contratto firmato da un sedicenne?",
            "answer": {
                "primary_answer": "No, un contratto firmato da un sedicenne (minore di età) è annullabile ai sensi dell'art. 1425 del Codice Civile. Il contratto può essere impugnato dal minore o dal suo rappresentante legale entro 5 anni dalla maggiore età (art. 1442 c.c.).",
                "confidence": 0.92,
                "legal_basis": [
                    {
                        "norm_id": "cc_1425",
                        "norm_title": "Codice Civile - Art. 1425",
                        "article": "1425",
                        "relevance": 0.95,
                        "excerpt": "Il contratto è annullabile se una delle parti era legalmente incapace di contrattare."
                    },
                    {
                        "norm_id": "cc_1442",
                        "norm_title": "Codice Civile - Art. 1442",
                        "article": "1442",
                        "relevance": 0.88,
                        "excerpt": "L'azione di annullamento si prescrive in cinque anni."
                    }
                ],
                "alternatives": [
                    {
                        "position": "Il contratto potrebbe essere considerato valido se il minore ha occultato la sua età con raggiri.",
                        "support_score": 0.15,
                        "expert_count": 1
                    }
                ],
                "uncertainty_preserved": True,
                "consensus_level": 0.85
            },
            "execution_trace": {
                "preprocessing": {"duration_ms": 245, "status": "completed"},
                "routing": {"duration_ms": 180, "status": "completed"},
                "retrieval": {"duration_ms": 420, "status": "completed"},
                "reasoning": {"duration_ms": 1850, "status": "completed"},
                "synthesis": {"duration_ms": 320, "status": "completed"},
                "total_duration_ms": 3015
            },
            "metadata": {
                "experts_consulted": ["literal_interpreter", "systemic_teleological", "principles_balancer"],
                "sources_count": 12,
                "iteration": 1
            },
            "timestamp": "2025-11-15T12:30:45Z"
        }
    },
    "uncertain_answer": {
        "summary": "Answer with Uncertainty",
        "description": "Answer where experts disagree significantly",
        "value": {
            "trace_id": "QRY-20251115140022-def456",
            "query": "È obbligatorio il Green Pass per accedere al posto di lavoro?",
            "answer": {
                "primary_answer": "La normativa sul Green Pass per l'accesso al posto di lavoro è stata oggetto di modifiche frequenti. Al momento attuale, la maggior parte degli obblighi è stata rimossa, ma permangono disposizioni specifiche per determinate categorie (personale sanitario, RSA). La situazione è in evoluzione.",
                "confidence": 0.65,
                "legal_basis": [
                    {
                        "norm_id": "dl_52_2021",
                        "norm_title": "D.L. 52/2021 (abrogato parzialmente)",
                        "article": "9-quinquies",
                        "relevance": 0.70,
                        "excerpt": "Disposizioni urgenti in materia di certificazioni verdi COVID-19..."
                    }
                ],
                "alternatives": [
                    {
                        "position": "L'obbligo permane per specifiche categorie professionali.",
                        "support_score": 0.40,
                        "expert_count": 2
                    },
                    {
                        "position": "Gli obblighi sono stati completamente rimossi per tutti i settori.",
                        "support_score": 0.35,
                        "expert_count": 1
                    }
                ],
                "uncertainty_preserved": True,
                "consensus_level": 0.55
            },
            "execution_trace": {
                "preprocessing": {"duration_ms": 210, "status": "completed"},
                "routing": {"duration_ms": 165, "status": "completed"},
                "retrieval": {"duration_ms": 380, "status": "completed"},
                "reasoning": {"duration_ms": 2150, "status": "completed"},
                "synthesis": {"duration_ms": 450, "status": "completed"},
                "total_duration_ms": 3355
            },
            "metadata": {
                "experts_consulted": ["literal_interpreter", "systemic_teleological", "precedent_analyst"],
                "sources_count": 8,
                "iteration": 2,
                "warning": "Normativa in evoluzione - verificare aggiornamenti recenti"
            },
            "timestamp": "2025-11-15T14:00:22Z"
        }
    },
    "quick_answer": {
        "summary": "Quick Answer (1 iteration)",
        "description": "Simple question answered in single iteration",
        "value": {
            "trace_id": "QRY-20251115151530-ghi789",
            "query": "Qual è l'età minima per votare in Italia?",
            "answer": {
                "primary_answer": "L'età minima per votare in Italia è 18 anni per la Camera dei Deputati e le elezioni locali. Per il Senato, l'età minima per votare è stata ridotta da 25 a 18 anni con la riforma costituzionale del 2020 (Legge Costituzionale n. 1/2020).",
                "confidence": 0.98,
                "legal_basis": [
                    {
                        "norm_id": "cost_48",
                        "norm_title": "Costituzione - Art. 48",
                        "article": "48",
                        "relevance": 1.0,
                        "excerpt": "Sono elettori tutti i cittadini, uomini e donne, che hanno raggiunto la maggiore età."
                    }
                ],
                "alternatives": [],
                "uncertainty_preserved": False,
                "consensus_level": 1.0
            },
            "execution_trace": {
                "preprocessing": {"duration_ms": 180, "status": "completed"},
                "routing": {"duration_ms": 120, "status": "completed"},
                "retrieval": {"duration_ms": 280, "status": "completed"},
                "reasoning": {"duration_ms": 950, "status": "completed"},
                "synthesis": {"duration_ms": 180, "status": "completed"},
                "total_duration_ms": 1710
            },
            "metadata": {
                "experts_consulted": ["literal_interpreter"],
                "sources_count": 3,
                "iteration": 1
            },
            "timestamp": "2025-11-15T15:15:30Z"
        }
    }
}

# ============================================================================
# USER FEEDBACK EXAMPLES
# ============================================================================

USER_FEEDBACK_EXAMPLES = {
    "positive_feedback": {
        "summary": "Positive Feedback",
        "description": "User satisfied with answer quality",
        "value": {
            "trace_id": "QRY-20251115123045-abc123",
            "rating": 5,
            "helpful": True,
            "issues": [],
            "comment": "Risposta molto chiara e completa. I riferimenti normativi sono precisi.",
            "user_id": "user_12345"
        }
    },
    "negative_with_correction": {
        "summary": "Negative with Correction",
        "description": "User found issues and provides corrections",
        "value": {
            "trace_id": "QRY-20251115140022-def456",
            "rating": 2,
            "helpful": False,
            "issues": ["incorrect", "incomplete"],
            "comment": "La risposta non considera la normativa più recente del 2024.",
            "correction": "Il D.L. 44/2024 ha modificato completamente il regime degli obblighi.",
            "user_id": "user_67890"
        }
    },
    "partial_satisfaction": {
        "summary": "Partial Satisfaction",
        "description": "Answer helpful but could be improved",
        "value": {
            "trace_id": "QRY-20251115151530-ghi789",
            "rating": 4,
            "helpful": True,
            "issues": [],
            "comment": "Buona risposta ma avrei gradito più dettagli sulla riforma del 2020.",
            "user_id": "user_11111"
        }
    }
}

# ============================================================================
# RLCF EXPERT FEEDBACK EXAMPLES
# ============================================================================

RLCF_FEEDBACK_EXAMPLES = {
    "expert_correction": {
        "summary": "Expert Correction",
        "description": "Legal expert provides detailed corrections",
        "value": {
            "trace_id": "QRY-20251115140022-def456",
            "expert_id": "expert_avv_rossi_001",
            "authority_score": 0.85,
            "corrections": {
                "answer_quality": "needs_revision",
                "legal_reasoning": "partially_correct",
                "legal_basis": "incomplete"
            },
            "suggested_changes": {
                "primary_answer": "La normativa sul Green Pass per l'accesso al posto di lavoro è stata abrogata dal D.L. 44/2023. Attualmente non sussistono obblighi generali, salvo per il personale sanitario (D.L. 73/2022).",
                "additional_legal_basis": [
                    {
                        "norm_id": "dl_44_2023",
                        "norm_title": "D.L. 44/2023 - Cessazione obblighi Green Pass",
                        "article": "1",
                        "relevance": 0.95,
                        "excerpt": "Sono abrogati gli obblighi di certificazione verde COVID-19..."
                    }
                ]
            },
            "detailed_comment": "La risposta non considera l'abrogazione completa degli obblighi avvenuta nel 2023. Solo il personale sanitario ha ancora obblighi residuali.",
            "vote_confidence": 0.92
        }
    },
    "expert_agreement": {
        "summary": "Expert Agreement",
        "description": "Expert confirms answer is correct",
        "value": {
            "trace_id": "QRY-20251115123045-abc123",
            "expert_id": "expert_prof_bianchi_002",
            "authority_score": 0.92,
            "corrections": {
                "answer_quality": "excellent",
                "legal_reasoning": "correct",
                "legal_basis": "complete"
            },
            "suggested_changes": {},
            "detailed_comment": "Risposta corretta e ben argomentata. I riferimenti normativi sono accurati e la spiegazione è chiara.",
            "vote_confidence": 0.98
        }
    }
}

# ============================================================================
# NER CORRECTION EXAMPLES
# ============================================================================

NER_CORRECTION_EXAMPLES = {
    "missing_entity": {
        "summary": "Missing Entity",
        "description": "Entity was not recognized by NER system",
        "value": {
            "trace_id": "QRY-20251115140022-def456",
            "query_text": "Il D.L. 52/2021 introduce l'obbligo di Green Pass",
            "entity_text": "D.L. 52/2021",
            "entity_type": "NORMA",
            "start_char": 3,
            "end_char": 15,
            "correction_type": "MISSING_ENTITY",
            "expert_id": "expert_ner_001",
            "comment": "Il decreto legge 52/2021 non è stato riconosciuto come entità NORMA."
        }
    },
    "wrong_entity_type": {
        "summary": "Wrong Entity Type",
        "description": "Entity recognized with incorrect type",
        "value": {
            "trace_id": "QRY-20251115123045-abc123",
            "query_text": "La Corte Costituzionale ha dichiarato illegittima la norma",
            "entity_text": "Corte Costituzionale",
            "entity_type": "GIURISDIZIONE",
            "start_char": 3,
            "end_char": 23,
            "correction_type": "WRONG_TYPE",
            "correct_entity_type": "ORGANO",
            "expert_id": "expert_ner_002",
            "comment": "La Corte Costituzionale è un ORGANO, non una GIURISDIZIONE."
        }
    }
}

# ============================================================================
# ERROR RESPONSE EXAMPLES
# ============================================================================

ERROR_RESPONSE_EXAMPLES = {
    "validation_error": {
        "summary": "Validation Error",
        "description": "Request validation failed (400)",
        "value": {
            "detail": [
                {
                    "loc": ["body", "query"],
                    "msg": "ensure this value has at least 10 characters",
                    "type": "value_error.any_str.min_length"
                }
            ],
            "body": {"query": "Breve"},
            "message": "Request validation failed. Check the 'detail' field for specific errors."
        }
    },
    "not_found": {
        "summary": "Resource Not Found",
        "description": "Query trace ID not found (404)",
        "value": {
            "detail": "Query with trace_id 'QRY-INVALID-123' not found."
        }
    },
    "timeout": {
        "summary": "Timeout Error",
        "description": "Query execution exceeded timeout (408)",
        "value": {
            "detail": "Query execution exceeded timeout limit",
            "trace_id": "QRY-20251115160000-timeout",
            "timeout_seconds": 120,
            "elapsed_seconds": 125
        }
    },
    "internal_error": {
        "summary": "Internal Server Error",
        "description": "Unexpected server error (500)",
        "value": {
            "detail": "Internal server error",
            "message": "An unexpected error occurred during query processing",
            "path": "/query/execute"
        }
    }
}
