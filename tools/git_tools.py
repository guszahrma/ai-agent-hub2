import subprocess
from pathlib import Path


PROTECTED_BRANCHES = {"main", "master"}


class GitError(Exception):
    pass


class SafetyError(Exception):
    """Raised when an operation is blocked by a safety guardrail."""
    pass


def _run(args: list, repo_path: str) -> str:
    path = Path(repo_path)
    if not path.exists():
        raise GitError(f"Repo path does not exist: {repo_path}")
    result = subprocess.run(
        ["git"] + args,
        cwd=path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = result.stderr.strip()
        if any(phrase in err.lower() for phrase in ["permission denied", "authentication failed", "could not read"]):
            raise GitError(f"Auth error — is SSH set up for this remote? ({err})")
        raise GitError(err)
    return result.stdout.strip()


# --- Read-only ---

def status(repo_path: str) -> str:
    return _run(["status", "--short"], repo_path)


def diff(repo_path: str, staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--staged")
    return _run(args, repo_path)


def log(repo_path: str, n: int = 10) -> str:
    return _run(["log", f"-{n}", "--oneline"], repo_path)


def branches(repo_path: str) -> str:
    return _run(["branch", "-a"], repo_path)


def current_branch(repo_path: str) -> str:
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)


# --- Write operations ---

def add(repo_path: str, files: list) -> str:
    return _run(["add"] + files, repo_path)


def commit(repo_path: str, message: str, author_name: str = None, author_email: str = None) -> str:
    args = []
    if author_name:
        args += ["-c", f"user.name={author_name}"]
    if author_email:
        args += ["-c", f"user.email={author_email}"]
    args += ["commit", "-m", message]
    return _run(args, repo_path)


def checkout(repo_path: str, branch: str, create: bool = False) -> str:
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch)
    return _run(args, repo_path)


def pull(repo_path: str, remote: str = "origin", branch: str = None) -> str:
    args = ["pull", remote]
    if branch:
        args.append(branch)
    return _run(args, repo_path)


def push(repo_path: str, remote: str = "origin", branch: str = None, confirmed: bool = False) -> str:
    target = branch or current_branch(repo_path)
    if target in PROTECTED_BRANCHES and not confirmed:
        raise SafetyError(
            f"Pushing to `{target}` is protected. "
            "Explicitly confirm by including 'confirmed=True' or asking the user to approve first."
        )
    args = ["push", remote]
    if branch:
        args.append(branch)
    return _run(args, repo_path)
