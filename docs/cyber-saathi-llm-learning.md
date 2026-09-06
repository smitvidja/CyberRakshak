# Cyber Saathi LLM Engineering Learning Artifact

This document ties common LLM concepts to concrete Session 9.4 decisions. CyberRakshak uses hosted inference, a small authoritative retrieval layer, deterministic safety playbooks, and post-generation validation. It does not train or run a large model on the development laptop.

## Concepts in the implementation

| Concept | Meaning | Cyber Saathi implementation decision |
|---|---|---|
| Transformer | The neural architecture behind the hosted Gemini, Grok, and Nemotron models. | The transformer runs at the provider. `MultiProviderLLMGateway` owns only bounded inference requests and never loads model weights locally. |
| Attention | The model mechanism that relates tokens inside its context. More context is not automatically better. | `PromptAssembler` labels and orders policy, role, incident state, compacted history, current input, retrieved knowledge, playbook, and output schema. Irrelevant datasets and unlimited history are excluded. |
| Embeddings | Numeric representations used to compare meaning or lexical similarity. | Session 9.3 uses a persisted 384-dimension Unicode-aware embedding for retrieving a few reviewed chunks. Those chunks—not the entire corpus—enter the LLM context. |
| Tokenization | Provider models split text into tokens and bill/enforce limits using their own tokenizer. | Before sending, Cyber Saathi uses a conservative character-based token estimate and rejects context above `LLM_MAX_INPUT_TOKENS`. Provider usage remains the final authority when live responses expose it. |
| Context window | The maximum input/history a model can process. A large advertised window should not justify sending everything. | Recent history is capped at six turns, older turns are deterministically compacted, RAG is capped at 2,200 characters, playbooks at 1,200 characters, and the total estimated input defaults to 3,000 tokens. |
| Inference | Running a trained model to produce a response. | Gemini uses its native REST contract; Grok and NVIDIA use their OpenAI-compatible hosted contracts. Provider selection and model IDs come from server configuration. |
| Temperature | Controls sampling variability. Lower values favour repeatability. | Defaults are `0.1` for safety/action, `0.25` for explanations, and `0.4` for normal conversation. Critical urgent financial guidance bypasses generation entirely. |
| Top-p | Restricts sampling to a probability mass. | `LLM_TOP_P=0.9` is centrally configured and combined with the response-type temperature rather than scattered through provider code. |
| Quantization | Lower-precision model weights can reduce serving memory/compute. | CyberRakshak performs no local quantization. NVIDIA's hosted Nemotron adapter remains API-only; any provider-side precision is a serving concern and does not consume laptop RAM. |
| Hallucination | A fluent output may contain unsupported or fabricated claims. | RAG chunk IDs are allow-listed, structured output is mandatory, amounts, transaction/UPI/contact values and helplines are checked against grounding, invented authority/legal/emergency actions and secret-shaped output are rejected, anonymous identity leakage is checked across supported language styles, and the gateway falls through to another provider or deterministic response. |
| Fine-tuning | Updating model weights for a task. | Session 9.4 deliberately does not fine-tune. The controlled understanding engine, authoritative RAG, structured prompts, playbooks, and evaluation provide a cheaper and more auditable first system. Fine-tuning is a future option only after enough reviewed examples and failure evidence exist. |

## Why validated streaming is buffered

The gateway exposes `stream()`, but it yields text only after the complete structured response passes validation. Showing raw partial tokens first could expose an unsafe claim and then discover the violation too late. Session 9.5 may stream voice or text at a higher layer while retaining this validation boundary.

## Provider references reviewed

- Gemini API keys and structured output: https://ai.google.dev/gemini-api/docs/api-key and https://ai.google.dev/gemini-api/docs/structured-output
- Grok authentication and structured output: https://docs.x.ai/developers/rest-api-reference/inference and https://docs.x.ai/developers/model-capabilities/text/structured-outputs
- NVIDIA hosted NIM API and Nemotron model ID: https://docs.api.nvidia.com/nim/reference/llm-apis and https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b

Provider contracts and model aliases can change. The environment defaults were reviewed on 2026-09-06; production deployment should pin or re-verify model IDs according to its stability requirements.
