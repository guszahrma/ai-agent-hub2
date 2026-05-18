import json
import re
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path(__file__).parent / "state"


class StateStore:
    """
    Sole writer of comment_state_PR[ID].json files in bot/state/.
    Agents report status changes to Hub Bot, which calls this class.
    All writes are atomic (write to .tmp, then rename).
    """

    def __init__(self):
        STATE_DIR.mkdir(exist_ok=True)
        self._states: dict[tuple[str, int], dict] = {}
        self._next_delegation_id: int = 1
        self._load_all()

    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _load_all(self):
        for path in sorted(STATE_DIR.glob("comment_state_*_PR*.json")):
            try:
                with open(path) as f:
                    state = json.load(f)
                key = (state["repo"], state["pr_number"])
                self._states[key] = state
                for thread in state.get("threads", {}).values():
                    for comment in thread.get("comments", []):
                        for d in comment.get("delegations", []):
                            if isinstance(d.get("id"), int):
                                self._next_delegation_id = max(
                                    self._next_delegation_id, d["id"] + 1
                                )
            except Exception as e:
                print(f"StateStore: failed to load {path}: {e}")

    def _path(self, repo_ref: str, pr_number: int) -> Path:
        repo_slug = re.sub(r'[^a-zA-Z0-9]', '_', repo_ref)
        return STATE_DIR / f"comment_state_{repo_slug}_PR{pr_number}.json"

    def _save(self, repo_ref: str, pr_number: int):
        key = (repo_ref, pr_number)
        state = self._states[key]
        state["last_updated"] = self._now()
        path = self._path(repo_ref, pr_number)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        tmp.rename(path)

    def _get_or_create(self, repo_ref: str, pr_number: int) -> dict:
        key = (repo_ref, pr_number)
        if key not in self._states:
            self._states[key] = {
                "pr_number": pr_number,
                "repo": repo_ref,
                "last_updated": self._now(),
                "threads": {},
            }
        return self._states[key]

    def _find_comment(self, state: dict, comment_id: str) -> tuple[dict | None, dict | None]:
        for thread in state["threads"].values():
            for c in thread.get("comments", []):
                if c["id"] == comment_id:
                    return thread, c
        return None, None

    # ── Public read API ──────────────────────────────────────────────────────

    def is_seen(self, repo_ref: str, pr_number: int, comment_id: int) -> bool:
        # Invariant: a comment absent from the store is treated identically to one
        # with status 'new' — both return False (not seen). This is intentional:
        # unseen comments must always be processed, regardless of whether they have
        # been recorded yet. Do not change either early-return to True.
        key = (repo_ref, pr_number)
        if key not in self._states:
            return False
        _, comment = self._find_comment(self._states[key], str(comment_id))
        if comment is None:
            return False
        return comment.get("status") != "new"

    def has_pr_state(self, repo_ref: str, pr_number: int) -> bool:
        return (repo_ref, pr_number) in self._states

    def warn_phantom_comments(self, repo_ref: str, pr_number: int, github_ids: set[int]):
        """Log warnings for comment IDs in state that are no longer on GitHub."""
        key = (repo_ref, pr_number)
        if key not in self._states:
            return
        for thread in self._states[key]["threads"].values():
            for comment in thread.get("comments", []):
                url = comment.get("url", "")
                if not url:
                    continue
                cid = int(comment["id"])
                if cid not in github_ids:
                    print(f"  [StateStore] Warning: comment {cid} in state but missing from GitHub (deleted?): {url}")

    def get_unresolved(self) -> list[dict]:
        """Return all comments with status 'delegated_to_scrum_master' or 'pending'."""
        result = []
        for (repo_ref, pr_number), state in self._states.items():
            for thread_id, thread in state["threads"].items():
                for comment in thread.get("comments", []):
                    if comment.get("status") in ("delegated_to_scrum_master", "pending"):
                        result.append({
                            "repo_ref": repo_ref,
                            "pr_number": pr_number,
                            "thread_id": thread_id,
                            "thread": thread,
                            "comment": comment,
                        })
        return result

    # ── Comment lifecycle ────────────────────────────────────────────────────

    def seed_comment(self, repo_ref: str, pr_number: int, comment_id: int,
                     thread_root_id: int, author: str, body: str, created_at: str,
                     url: str, path: str, original_line: int, comment_type: str,
                     anchored_arbitrarily: bool = False, status: str = "resolved"):
        """Seed a comment with a known status (default resolved, for first-ever poll)."""
        self._upsert_comment(
            repo_ref, pr_number, comment_id, thread_root_id, author, body,
            created_at, url, path, original_line, comment_type, status=status,
            anchored_arbitrarily=anchored_arbitrarily,
        )

    def add_new_comment(self, repo_ref: str, pr_number: int, comment_id: int,
                        thread_root_id: int, author: str, body: str, created_at: str,
                        url: str, path: str, original_line: int, comment_type: str):
        """Add a newly detected comment with status 'new'."""
        self._upsert_comment(
            repo_ref, pr_number, comment_id, thread_root_id, author, body,
            created_at, url, path, original_line, comment_type, status="new",
        )

    def _upsert_comment(self, repo_ref: str, pr_number: int, comment_id: int,
                        thread_root_id: int, author: str, body: str, created_at: str,
                        url: str, path: str, original_line: int, comment_type: str,
                        status: str, anchored_arbitrarily: bool = False):
        state = self._get_or_create(repo_ref, pr_number)
        thread_key = str(thread_root_id)

        if thread_key not in state["threads"]:
            state["threads"][thread_key] = {
                "type": comment_type,
                "path": path,
                "original_line": original_line,
                "anchored_arbitrarily": anchored_arbitrarily,
                "status": status,
                "comments": [],
            }

        thread = state["threads"][thread_key]
        existing = {c["id"] for c in thread["comments"]}
        if str(comment_id) not in existing:
            thread["comments"].append({
                "id": str(comment_id),
                "url": url,
                "author": author,
                "created_at": created_at,
                "body_snippet": body[:80],
                "status": status,
            })
        self._save(repo_ref, pr_number)

    def resolve_thread(self, repo_ref: str, pr_number: int, thread_root_id: int):
        """Mark a thread as resolved based on GitHub's Resolve Conversation signal."""
        key = (repo_ref, pr_number)
        if key not in self._states:
            return
        thread = self._states[key]["threads"].get(str(thread_root_id))
        if thread is None or thread.get("status") == "resolved":
            return
        thread["status"] = "resolved"
        self._save(repo_ref, pr_number)

    def set_comment_status(self, repo_ref: str, pr_number: int, comment_id: int,
                           status: str, resolved_by: int = None):
        state = self._get_or_create(repo_ref, pr_number)
        thread, comment = self._find_comment(state, str(comment_id))
        if comment is None:
            return
        comment["status"] = status
        if resolved_by is not None:
            comment["resolved_by"] = str(resolved_by)
        if thread:
            self._derive_thread_status(thread)
        self._save(repo_ref, pr_number)

    # ── Delegation lifecycle ─────────────────────────────────────────────────

    def add_delegation(self, repo_ref: str, pr_number: int, comment_id: int,
                       agent: str, task: str) -> int:
        """Add a delegation item to a comment. Returns the delegation ID."""
        state = self._get_or_create(repo_ref, pr_number)
        _, comment = self._find_comment(state, str(comment_id))
        if comment is None:
            return -1
        delegation_id = self._next_delegation_id
        self._next_delegation_id += 1
        comment.setdefault("delegations", []).append({
            "id": delegation_id,
            "delegated_at": self._now(),
            "agent": agent,
            "task": task,
            "status": "pending",
        })
        self._save(repo_ref, pr_number)
        return delegation_id

    def set_delegation_status(self, repo_ref: str, pr_number: int,
                               delegation_id: int, status: str, **kwargs):
        """Update a delegation's status. Derives comment and thread status afterwards."""
        state = self._get_or_create(repo_ref, pr_number)
        for thread in state["threads"].values():
            for comment in thread.get("comments", []):
                for d in comment.get("delegations", []):
                    if d["id"] == delegation_id:
                        d["status"] = status
                        d.update(kwargs)
                        self._derive_comment_status(comment)
                        self._derive_thread_status(thread)
                        self._save(repo_ref, pr_number)
                        return

    # ── Derived status rules ─────────────────────────────────────────────────

    def _derive_comment_status(self, comment: dict):
        delegations = comment.get("delegations", [])
        if not delegations:
            return
        statuses = {d["status"] for d in delegations}
        if all(s in ("resolved", "superseded") for s in statuses) and "resolved" in statuses:
            comment["status"] = "resolved"

    def _derive_thread_status(self, thread: dict):
        comments = thread.get("comments", [])
        if not comments:
            return
        statuses = {c.get("status") for c in comments}
        if statuses == {"resolved"}:
            thread["status"] = "resolved"
        elif "pending" in statuses:
            thread["status"] = "pending"
        elif "awaiting_user" in statuses:
            thread["status"] = "awaiting_user"
        elif "delegated_to_scrum_master" in statuses:
            thread["status"] = "delegated_to_scrum_master"
        elif "new" in statuses:
            thread["status"] = "new"
