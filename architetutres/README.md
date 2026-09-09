# CyberRakshak Architecture Diagrams

These documents describe the current implementation, not a planned future stack.

1. [RAG architecture](./01-current-rag-architecture.md)
2. [RAG request pipeline](./02-rag-request-pipeline.md)
3. [LLM gateway architecture](./03-llm-architecture.md)
4. [Full frontend, backend, database, and storage architecture](./04-full-stack-architecture.md)

## Important current boundaries

- Cyber Saathi uses a reviewed, file-backed knowledge index. It does **not** use a hosted vector database or rebuild embeddings when the API starts.
- Urgent safety guidance, critical-entity confirmation, and report handoff remain deterministic backend workflows; an LLM cannot override them.
- LLM keys, raw prompts, and provider responses stay on the server.
- PostgreSQL stores relational data and consented/redacted conversation state. Object storage owns uploaded evidence files; PostgreSQL stores only their metadata.
