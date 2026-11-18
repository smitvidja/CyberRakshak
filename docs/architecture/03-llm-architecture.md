# LLM Architecture

## Role of the LLM

The LLM is optional enrichment inside Cyber Saathi. It can phrase grounded guidance, but it does not own classification, urgent safety actions, entity confirmation, authorization, report readiness, or persistence.

```mermaid
flowchart TD
  S[CyberSaathiService] --> E{LLM enabled and generation eligible?}
  E -->|No| D[Deterministic grounded response]
  E -->|Yes| P[PromptAssembler]

  subgraph BoundedInput[Bounded server-side prompt]
    P --> I[Incident state without excess summary]
    P --> H[Recent turns: maximum 6]
    P --> O[Older-turn compact summary]
    P --> K[Retrieved context: maximum 2,200 chars]
    P --> SP[Deterministic playbook: maximum 1,200 chars]
    P --> C[Prompt contract + required JSON schema]
  end

  BoundedInput --> G[MultiProviderLLMGateway]
  G --> G1[Configured primary provider]
  G1 -->|Unavailable, timeout, invalid or rejected| G2[Configured secondary provider]
  G2 -->|Unavailable, timeout, invalid or rejected| G3[Configured tertiary provider]
  G3 -->|All attempts fail| D

  G1 --> V[Structured response validation]
  G2 --> V
  G3 --> V
  V --> R{Valid and safe?}
  R -->|No| D
  R -->|Yes| A[Grounded assistant response]
```

## Provider adapters

| Adapter | Protocol | Notes |
| --- | --- | --- |
| Gemini | Google `generateContent` API | Uses Gemini's compatible response-schema dialect |
| Grok | OpenAI-compatible chat-completions API | Strict schema requested |
| NVIDIA | OpenAI-compatible chat-completions API | Provider/model are configuration-driven |

The configured primary, secondary, and tertiary order comes from server settings. Credentials are read only on the backend; the frontend never receives a provider key, raw prompt, raw response, or provider error body.

## Validation and fallback gates

```mermaid
flowchart LR
  A[Provider JSON] --> B[Pydantic structured schema]
  B --> C[Allowed retrieved source IDs only]
  C --> D[Safety validator]
  D --> E{No prohibited claims or unsafe instructions?}
  E -->|Yes| F[Assistant turn with safe observability]
  E -->|No| G[Reject provider output]
  G --> H[Try next provider or deterministic fallback]

  F --> I[provider, model, fallback flag, latency, safety flags]
```

The safety validator rejects outputs that claim access to banks/government/police systems, promise recovery, make legal or criminality conclusions, disclose prompts, expose secrets, or cite chunks that were not retrieved. A deadline, malformed JSON, provider failure, or safety rejection follows the same safe fallback path.
