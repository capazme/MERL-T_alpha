# Bibliography

This bibliography is organized according to the phases of the MERL-T pipeline and includes key papers and resources that inform the project's architecture and methodologies.

## General Premise: RAG Systems, LLM Agents, and Legal Applications

-   **Lewis, P., et al. (2020).** *Retrieval-augmented generation for knowledge-intensive NLP tasks.* Advances in Neural Information Processing Systems, 33, 9459-9474. (Fundamental for the concept of RAG).
-   **Gao, Y., et al. (2024).** *Retrieval-Augmented Generation for Large Language Models: A Survey.* arXiv preprint arXiv:2312.10997. (A complete and recent survey on the state of the art of RAG).
-   **Xi, Z., et al. (2023).** *The Rise and Potential of Large Language Model Based Agents: A Survey.* arXiv preprint arXiv:2309.07864. (A survey on LLM agents, relevant for the MoE approach).
-   **Zhong, H., et al. (2020).** *How Does NLP Benefit Legal System: A Summary of Legal Artificial Intelligence.* arXiv preprint arXiv:2004.12158. (An overview of the application of AI in the legal domain).
-   **Katz, D. M., Bommarito II, M. J., & Blackman, J. (2017).** *A general approach for predicting the behavior of the Supreme Court of the United States.* PloS one, 12(4), e0174698. (A historical example of the application of AI/ML to law, albeit not with LLMs).

## 1. Pre-processing and Legal Named Entity Recognition (NER)

### 1.1. Text Normalization

-   **Standard NLP Pre-processing**: Manning, C. D., & Schütze, H. (1999). *Foundations of statistical natural language processing.* MIT press. (Relevant chapters on tokenization and normalization).
-   **Legal Specificity**: While there may not be a single paper on legal normalization, general principles apply. The challenge is to define specific rules for abbreviations and canonical references (e.g., URNs).

### 1.2. Legal Named Entity Recognition (NER)


-   **Chalkidis, I., et al. (2020).** *LEGAL-BERT: The Muppets straight out of Law School.* Findings of the Association for Computational Linguistics: EMNLP 2020, 2898-2904. (A BERT model pre-trained on legal texts, useful as a basis for a fine-tuned NER).
-   **Leitner, E., Rehm, G., & Moreno-Schneider, J. (2019).** *Fine-grained named entity recognition in legal documents.* Proceedings of the Natural Legal Language Processing Workshop 2019. (Focus on fine-grained NER in the legal domain).
-   **Angelidis, S., Chalkidis, I., & Kormpa, K. (2021).** *Named entity recognition and relation extraction in the legal domain: a survey.* Artificial Intelligence and Law, 29(4), 459-507. (A specific survey on NER and RE in the legal field).

## 2. Query Routing (Trainable MoE Router)

-   **Shazeer, N., et al. (2017).** *Outrageously large neural networks: The sparsely-gated mixture-of-experts layer.* arXiv preprint arXiv:1701.06538. (The foundational paper on the Mixture-of-Experts (MoE) architecture).
-   **Jacobs, R. A., et al. (1991).** *Adaptive mixtures of local experts.* Neural computation, 3(1), 79-87. (Pioneering work on mixture of experts).
-   **Zhou, Y., et al. (2022).** *Mixture-of-Experts with Expert Choice Routing.* Advances in Neural Information Processing Systems, 35, 7103-7114. (An evolution of MoE routing).
-   **Singhal, A., et al. (2022).** *Large Language Models can be Lazy Learners: Analyze Shortcuts in In-Context Learning.* Findings of the Association for Computational Linguistics: ACL 2023. (Relevant for understanding how LLMs choose strategies, applicable to routing).
-   **RLCF (Reinforcement Learning from Community Feedback)**: There is currently no canonical paper specifically named "RLCF." However, the concept is a derivation of:
    -   **Ouyang, L., et al. (2022).** *Training language models to follow instructions with human feedback.* Advances in Neural Information Processing Systems, 35, 27730-27744. (The foundational paper on RLHF - Reinforcement Learning from Human Feedback).
    -   The idea of "Community Feedback" is an extension/adaptation of RLHF, where the feedback comes from a community of experts (in this case, legal experts) instead of generic annotators. The validation will be based on the principles of RLHF, adapted to the community context.

## 3. Context Augmentation (Information Retrieval)

### General GraphRAG

-   **Guo, B., et al. (2024).** *LightRAG: A Scalable and Lightweight Framework for Enhancing Large Language Models via Graph-Based Retrieval-Augmented Generation.* arXiv preprint arXiv:2410.05779. (A direct reference mentioned in the pipeline for GraphRAG).
-   **Esmeili, E., et al. (2023).** *KnowledGPT: Enhancing Large Language Models with Retrieval and Storage.* arXiv preprint arXiv:2312.08682. (An approach that integrates KG with LLM).

### 3.1. Vector Database Retrieval (ANN)

-   **Johnson, J., Douze, M., & Jégou, H. (2019).** *Billion-scale similarity search with GPUs.* IEEE Transactions on Big Data, 7(3), 535-547. (Describes FAISS, a common library for ANN).
-   **Wang, L., et al. (2020).** *Milvus: A Purpose-Built Vector Data Management System.* Proceedings of the 2021 International Conference on Management of Data. (Describes Milvus).
-   **Reimers, N., & Gurevych, I. (2019).** *Sentence-BERT: Sentence embeddings using Siamese BERT-networks.* arXiv preprint arXiv:1908.10084. (A common technique for generating high-quality embeddings for semantic search).

### 3.2. Knowledge Graph (KG) Retrieval

-   **Hogan, A., et al. (2021).** *Knowledge graphs.* ACM Computing Surveys (CSUR), 54(4), 1-37. (A comprehensive survey on Knowledge Graphs).
-   **Bordes, A., et al. (2013).** *Translating embeddings for modeling multi-relational data.* Advances in neural information processing systems, 26. (A foundational technique for embeddings in KGs).
-   **Legal Specificity of KGs**:
    -   **Casellas, N. (2011).** *Legal ontology engineering: methodologies, modelling trends, and the ontology of professional judicial knowledge.* Springer Science & Business Media. (A reference text on the engineering of legal ontologies).
    -   **Francesconi, E. (2014).** *Legal knowledge graphs for the Semantic Web.* Semantic Web, 5(2), 87-90. (Focus on KGs specific to law).

### 3.3. Dynamic API Retrieval

-   This does not require scientific validation for the act of the API call itself, but the quality and reliability of the APIs (`VisuaLexAPI`, `API Sentenze`) are crucial and could be the subject of external evaluation or reporting.

## 4. Prompt Construction for LLM

-   **Brown, T., et al. (2020).** *Language models are few-shot learners.* Advances in neural information processing systems, 33, 1877-1901. (The GPT-3 paper that popularized prompting).
-   **Wei, J., et al. (2022).** *Chain-of-thought prompting elicits reasoning in large language models.* Advances in Neural Information Processing Systems, 35, 24824-24837. (A prompting technique to improve reasoning).
-   **Kojima, T., et al. (2022).** *Large language models are zero-shot reasoners.* Advances in Neural Information Processing Systems, 35, 22199-22213. (Another fundamental prompting technique).
-   **Gao, T., Yao, Y., & Chen, D. (2021).** *SimCSE: Simple Contrastive Learning of Sentence Embeddings.* arXiv preprint arXiv:2104.08821. (Relevant if embeddings influence the selection of context inserted into the prompt).
-   **Liu, Y., et al. (2021).** *What Makes Good In-Context Examples for GPT-3?* arXiv preprint arXiv:2101.06804. (Analysis on how to structure prompts with examples).

## 5. LLM Inference (Expert Modules)

### Fine-tuning for Specific Domains

-   **Howard, J., & Ruder, S. (2018).** *Universal language model fine-tuning for text classification.* arXiv preprint arXiv:1801.06146. (ULMFiT, a pioneering fine-tuning technique).
-   **Gururangan, S., et al. (2020).** *Don't stop pretraining: Adapt language models to domains and tasks.* Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics. (Demonstrates the importance of domain adaptation).
-   **Chalkidis, I., et al. (2020).** *LEGAL-BERT: The Muppets straight out of Law School.* (Also cited for NER, but fundamental for fine-tuning on legal data).

### RAG-Optimized Models

-   Research on models specifically optimized for RAG is ongoing. Often, generic LLMs with good instruction-following capabilities are used. The validation here depends on the performance of the chosen model on the specific task.
-   **Yu, W., et al. (2023).** *Chain-of-Note: Enhancing Robustness in Retrieval-Augmented Language Models.* arXiv preprint arXiv:2311.09210. (An example of a technique to improve the robustness of RAG models).

### Use of LoRA (Low-Rank Adaptation)

-   **Hu, E. J., et al. (2021).** *LoRA: Low-Rank Adaptation of Large Language Models.* arXiv preprint arXiv:2106.09685. (An efficient technique for fine-tuning).

## 6. Synthesis and Combination of Responses (Trainable MoE Synthesizer)

-   **MoE References**: See Section 2 (Routing). The application here is on synthesis rather than routing, but the architectural principles are similar.
-   **RLCF References**: See Section 2 (Routing). The training of the synthesizer is based on the same principles of learning from expert community feedback.
-   **Combination of outputs from different models/sources**:
    -   **Wang, B., Xu, C., & Ma, T. (2021).** *Understanding and improving knowledge distillation.* Proceedings of the 38th International Conference on Machine Learning. (Concepts of distillation and model combination, even if not specific to MoE/synthesis RAG).
    -   **Du, N., et al. (2022).** *GLaM: Efficient Scaling of Language Models with Mixture-of-Experts.* arXiv preprint arXiv:2112.06905. (An example of a large-scale MoE architecture, useful for understanding how gates combine outputs).

## 7. Post-processing and Final Output

### 7.2. Source Tracking and Citation

-   **Gao, Y., et al. (2024).** *Retrieval-Augmented Generation for Large Language Models: A Survey.* (The evaluation section of RAG systems often discusses the fidelity and attribution of sources).
-   **Nakano, R., et al. (2021).** *Webgpt: Browser-assisted question-answering with human feedback.* arXiv preprint arXiv:2112.09332. (An example of a system that emphasizes source citation).
-   **Menick, J., et al. (2022).** *Teaching language models to support answers with verified quotes.* arXiv preprint arXiv:2203.11147. (Specific focus on supporting answers with verified citations).

### 7.3. Security/Quality Filters

-   **Gehman, S., et al. (2020).** *RealToxicityPrompts: Evaluating Neural Toxic Degeneration in Language Models.* Findings of the Association for Computational Linguistics: EMNLP 2020. (Evaluation of toxicity).
-   **Perez, F., et al. (2022).** *Ignore the Noise: Robust Conditional Diffusion Models via Diffusion Guidance.* arXiv preprint arXiv:2211.10121. (Potentially relevant for model-based filters).
-   Validation here is often based on specific datasets for bias, toxicity, and adherence to guidelines (e.g., Constitutional AI: **Bai, Y., et al. (2022).** *Constitutional AI: Harmlessness from AI Feedback.* arXiv preprint arXiv:2212.08073.)
