from pathlib import Path
from agent_directory.ollama_agent import OllamaAgent


SYSTEM_PROMPT = """You are a Junior Test Engineer AI agent.

Your job is to write pytest unit tests for existing Python code.

Given source code you will:
1. Identify all public functions, methods, and classes
2. Write comprehensive tests covering:
   - Happy path (normal, valid inputs)
   - Edge cases (empty inputs, None, boundary values)
   - Error cases (invalid inputs, expected exceptions)
3. Mock external dependencies (HTTP calls, file I/O, databases) using unittest.mock
4. Use descriptive test names: test_<function>_<scenario>
5. Group tests in classes per module under test

Output a single valid Python file. No explanation outside the code."""


def _strip_fences(text: str) -> str:
    if "```" not in text:
        return text
    lines = text.splitlines()
    inner, in_block = [], False
    for line in lines:
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if in_block:
            inner.append(line)
    return "\n".join(inner) if inner else text


class JuniorTestEngineer(OllamaAgent):
    def __init__(self):
        super().__init__(
            name="junior_test_engineer",
            system_prompt=SYSTEM_PROMPT,
        )

    def generate_tests(self, source_code: str, filename: str) -> str:
        """Return pytest source for the given Python file content."""
        result = self.run([
            {
                "role": "user",
                "content": (
                    f"Write pytest unit tests for `{filename}`:\n\n"
                    f"```python\n{source_code}\n```"
                ),
            }
        ])
        self.reflect(
            f"Generated tests for {filename}.\n"
            f"Source lines: {len(source_code.splitlines())}\n"
            f"Output preview: {result[:300]}"
        )
        return _strip_fences(result)

    def execute(self, task: str, repo_ref: str = None, repo_path: str = None, pr_number: int = None) -> str | None:
        if not repo_path:
            return "No repo_path provided."

        candidates = [
            f for f in self.list_local_files(repo_path, "**/*.py")
            if not Path(f).name.startswith("test_")
            and "test" not in Path(f).parts
            and Path(f).name != "__init__.py"
        ]

        written = []
        for rel_path in candidates:
            source = self.read_local_file(repo_path, rel_path)
            if not source or len(source.strip()) < 50:
                continue

            test_content = self.generate_tests(source, rel_path)
            p = Path(rel_path)
            test_path = str(p.parent / f"test_{p.name}")
            self.write_local_file(repo_path, test_path, test_content)
            written.append(test_path)

        return f"Generated {len(written)} test file(s): {', '.join(written)}"
