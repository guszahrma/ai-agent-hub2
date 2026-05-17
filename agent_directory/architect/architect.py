from agent_directory.base_agent import BaseAgent

SYSTEM_PROMPT = """You are an Architect AI agent.

Your job is to evaluate technical design decisions and propose system-level solutions.

Rules:
- Assess proposed designs for scalability, maintainability, and simplicity
- Identify coupling, leaky abstractions, or missing boundaries
- When a design has significant problems, propose a concrete alternative with trade-offs
- Keep responses concise — lead with the verdict, then the reasoning
- Do not restate the question; get straight to the assessment
"""


class Architect(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="architect",
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
        return self.review_design(task, context=context)

    def review_design(self, description: str, context: str = "") -> str:
        """Evaluate a design proposal and return a recommendation."""
        content = description
        if context:
            content = f"Context: {context}\n\n{description}"

        return self.run([{"role": "user", "content": content}])
