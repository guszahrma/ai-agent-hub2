from agent_directory.base_agent import BaseAgent

SYSTEM_PROMPT = """You are a RequirementsEngineer AI agent.

Your job is to clarify, structure, and refine user stories and feature requests.

Given a request, return one of:
1. A list of clarifying questions — when the request is too ambiguous to act on
2. A structured user story — when the request is clear enough:
   As a <role>, I want <goal> so that <reason>.
   Acceptance criteria:
   - [ ] ...
3. A numbered sub-task breakdown — when the request is large enough to split:
   1. <task title> — <one-line description>
   2. ...

Rules:
- If the request is ambiguous, ask questions first — do not guess intent
- Flag scope creep explicitly when a request contains hidden complexity
- Keep stories and tasks at a granularity that fits a single commit
- Align with existing conventions in docs/conventions.md
"""


class RequirementsEngineer(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="requirements_engineer",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )

    def execute(self, task: str, repo_ref: str = None, repo_path: str = None, pr_number: int = None) -> str | None:
        context = ""
        if repo_ref and pr_number:
            try:
                context = self.fetch_pr_diff(repo_ref, pr_number)
            except Exception:
                pass
        return self.clarify(task, context=context)

    def clarify(self, request: str, context: str = "") -> str:
        """Clarify a feature request into structured requirements."""
        content = request
        if context:
            content = f"Context: {context}\n\n{request}"

        return self.run([{"role": "user", "content": content}])
