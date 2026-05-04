import subprocess
from pathlib import Path


class GitError(Exception):
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
        raise GitError(result.stderr.strip())
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


def push(repo_path: str, remote: str = "origin", branch: str = None) -> str:
    args = ["push", remote]
    if branch:
        args.append(branch)
    return _run(args, repo_path)
