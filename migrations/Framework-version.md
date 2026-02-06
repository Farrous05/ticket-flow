# Framework Reference — LangGraph

This project’s workflow engine is built using **LangGraph**.

LangGraph is used to provide:
- Deterministic DAG-based execution
- Explicit state transitions between steps
- Checkpointing and resume semantics
- Clear separation between nodes (agents) and tools

All workflow design and execution assumptions in this project are constrained to **documented, stable LangGraph behavior**.

## Reference
- Official repository and documentation:
  https://github.com/langchain-ai/langgraph

## Scope
This reference is provided for **conceptual grounding only**.
The project does not reimplement, modify, or extend LangGraph internals.

No undocumented or speculative LangGraph features are assumed.
