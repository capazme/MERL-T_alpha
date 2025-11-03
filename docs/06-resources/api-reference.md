# MERL-T API Reference

## 1. Introduction

The MERL-T platform is built on a service-oriented architecture, with a central API Gateway that provides a unified interface to all the underlying services. This document provides a high-level overview of the MERL-T API. For detailed, interactive documentation, please refer to the links in the section below.

## 2. Interactive API Documentation

MERL-T uses FastAPI, which automatically generates interactive API documentation based on the OpenAPI specification.

-   **Swagger UI**: `http://<your-merlt-instance>/docs`
    -   An interactive UI where you can explore the API endpoints, view the request and response models, and even send test requests directly from your browser.

-   **ReDoc**: `http://<your-merlt-instance>/redoc`
    -   An alternative, more documentation-focused UI for viewing the API specification.

## 3. High-Level Overview of API Endpoints

The MERL-T API is organized into several logical groups of endpoints:

### User Management

-   Endpoints for creating, retrieving, and managing users of the platform.
-   Includes endpoints for managing user credentials, which are a key component of the RLCF framework's Dynamic Authority scoring.

### Task Management

-   Endpoints for creating and managing legal tasks within the RLCF framework.
-   Supports the creation of various task types (e.g., QA, Classification, Summarization) with dynamic input schemas.

### Feedback Management

-   Endpoints for submitting and retrieving community feedback on AI-generated responses.
-   This is the core of the RLCF feedback loop, allowing the community to provide the data needed to train and improve the system.

### RLCF Governance

-   Endpoints for managing and monitoring the RLCF process, including:
    -   Retrieving authority scores and leaderboards.
    -   Viewing bias reports.
    -   Managing the Devil's Advocate system.

### Query Pipeline

-   The main endpoint for submitting a legal query to the MERL-T pipeline.
-   This endpoint orchestrates the entire process, from pre-processing and NER to routing, context augmentation, LLM inference, and synthesis.

### Knowledge Graph and Vector Store

-   Internal endpoints for interacting with the Neo4j Knowledge Graph and the ChromaDB Vector Store.
-   These are typically not exposed directly to the end-user but are used by the other services in the pipeline.

For detailed information on each endpoint, including the required parameters, request bodies, and response models, please refer to the interactive Swagger UI or ReDoc documentation.
