# JuniorTestEngineer Agent

## Purpose
The JuniorTestEngineer generates pytest unit tests for existing Python source files. It runs locally via Ollama (qwen2.5-coder:7b) and does not require an Anthropic API key.

## Responsibilities
- Read Python source files from a local repository
- Generate comprehensive pytest unit tests covering happy paths, edge cases, and error cases
- Write test files alongside the source (e.g. `foo.py` → `test_foo.py`)
- Mock external dependencies (HTTP, file I/O, databases)

## Interaction model
JuniorTestEngineer is not Discord-facing. It is called by the ScrumMaster when a code change needs test coverage.

**Addressing syntax in a PR comment:**
```
**[ScrumMaster] → [JuniorTestEngineer]:** please generate tests for the code in PR #N
```
