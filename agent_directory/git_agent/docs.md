# GitAgent

GitAgent is a shared git specialist. All agents that need git operations delegate to it rather than implementing git logic themselves.

## Role

- Executes git read operations: `status`, `diff`, `log`, `branches`, `current_branch`
- Executes git write operations: `add`, `commit`, `checkout`, `pull`, `push`
- Enforces safety guardrails (e.g. blocks force push, protects main branch)
- Attributes commits with its own git identity (`git_name` / `git_email` from `config/agents.yaml`)

## Communication pattern

GitAgent is not Discord-facing. It is called programmatically by other agents.

**Current mechanism — ScrumMaster delegation via Anthropic tool use:**

1. A user message arrives in Discord and is passed to ScrumMaster
2. ScrumMaster's LLM decides the request is git-related and emits a `delegate_to_git_agent` tool call
3. ScrumMaster calls `GitAgent.handle(request, repo_path)`
4. GitAgent gathers repo context (branch, status, recent log), sends it with the request to its own LLM, and returns a plain-text result
5. ScrumMaster receives the result and incorporates it into its reply

**Addressing GitAgent from a PR comment:**

Use the addressing syntax from `workprocess.md`:
```
**[ScrumMaster] → [GitAgent]:** please check the current branch status
```
ScrumMaster is responsible for routing addressed requests to GitAgent.

## Safety guardrails

- Force push is always blocked
- Write operations to protected branches raise `SafetyError` before touching git
- Protected branches are configured in `config/agents.yaml`

## Config

```yaml
# config/agents.yaml
agents:
  git_agent:
    model: claude-haiku-4-5-20251001
    git_name: GitAgent
    git_email: git-agent@ai-agent-hub2
```
