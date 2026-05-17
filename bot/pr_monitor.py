import os
import re
import requests
from dataclasses import dataclass, field
from datetime import datetime

from bot.state_store import StateStore


GITHUB_API = "https://api.github.com"


@dataclass
class PRComment:
    pr_number: int
    pr_title: str
    comment_id: int
    comment_type: str  # "review" (inline) or "issue" (general)
    author: str
    body: str
    created_at: str
    url: str
    diff_hunk: str = ""
    in_reply_to_id: int = None
    path: str = ""          # review comments only
    original_line: int = None  # review comments only


class PRMonitor:
    """Polls GitHub for new PR comments on a given repo."""

    def __init__(self, github_token: str, state_store: StateStore):
        self._token = github_token
        self._state_store = state_store
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        self._open_pr_numbers: dict[str, set] = {}

    def _get(self, url: str, params: dict = None) -> list:
        results = []
        while url:
            resp = self._session.get(url, params=params)
            resp.raise_for_status()
            results.extend(resp.json())
            url = resp.links.get("next", {}).get("url")
            params = None
        return results

    def _open_prs(self, repo_ref: str) -> list[dict]:
        return self._get(f"{GITHUB_API}/repos/{repo_ref}/pulls", params={"state": "open", "per_page": 100})

    def detect_merged_prs(self, repo_ref: str, current_prs: list[dict]) -> list[dict]:
        current_numbers = {pr["number"] for pr in current_prs}
        known = self._open_pr_numbers.get(repo_ref)

        if known is None:
            self._open_pr_numbers[repo_ref] = current_numbers
            return []

        merged_numbers = known - current_numbers
        self._open_pr_numbers[repo_ref] = current_numbers

        if not merged_numbers:
            return []

        merged = []
        for num in merged_numbers:
            resp = self._session.get(f"{GITHUB_API}/repos/{repo_ref}/pulls/{num}")
            if resp.ok:
                pr = resp.json()
                if pr.get("merged_at"):
                    merged.append(pr)
        return merged

    def poll(self, repo_ref: str) -> tuple[list[PRComment], list[dict]]:
        """Return (new_comments, merged_prs) since last poll."""
        try:
            prs = self._open_prs(repo_ref)
        except requests.HTTPError as e:
            raise RuntimeError(f"GitHub API error fetching PRs for {repo_ref}: {e}")

        merged_prs = self.detect_merged_prs(repo_ref, prs)
        pr_titles = {pr["number"]: pr["title"] for pr in prs}
        new_comments: list[PRComment] = []

        # Inline review comments
        try:
            review_comments = self._get(
                f"{GITHUB_API}/repos/{repo_ref}/pulls/comments",
                params={"per_page": 100, "sort": "created", "direction": "asc"},
            )
        except requests.HTTPError as e:
            print(f"PR poll warning: failed to fetch review comments for {repo_ref}: {e}")
            review_comments = []

        for c in review_comments:
            cid = c["id"]
            pr_num = int(c["pull_request_url"].split("/")[-1])
            if pr_num not in pr_titles:
                continue

            is_first_pr_poll = not self._state_store.has_pr_state(repo_ref, pr_num)
            thread_root_id = c.get("in_reply_to_id") or cid

            if self._state_store.is_seen(repo_ref, pr_num, cid):
                continue

            if is_first_pr_poll or c["body"].startswith("**["):
                self._state_store.seed_comment(
                    repo_ref=repo_ref, pr_number=pr_num, comment_id=cid,
                    thread_root_id=thread_root_id,
                    author=c["user"]["login"], body=c["body"],
                    created_at=c["created_at"], url=c["html_url"],
                    path=c.get("path", ""), original_line=c.get("original_line"),
                    comment_type="review",
                )
            else:
                self._state_store.add_new_comment(
                    repo_ref=repo_ref, pr_number=pr_num, comment_id=cid,
                    thread_root_id=thread_root_id,
                    author=c["user"]["login"], body=c["body"],
                    created_at=c["created_at"], url=c["html_url"],
                    path=c.get("path", ""), original_line=c.get("original_line"),
                    comment_type="review",
                )
                new_comments.append(PRComment(
                    pr_number=pr_num,
                    pr_title=pr_titles[pr_num],
                    comment_id=cid,
                    comment_type="review",
                    author=c["user"]["login"],
                    body=c["body"],
                    created_at=c["created_at"],
                    url=c["html_url"],
                    diff_hunk=c.get("diff_hunk", ""),
                    in_reply_to_id=c.get("in_reply_to_id"),
                    path=c.get("path", ""),
                    original_line=c.get("original_line"),
                ))

        # General issue comments on each open PR
        for pr in prs:
            pr_num = pr["number"]
            is_first_pr_poll = not self._state_store.has_pr_state(repo_ref, pr_num)
            try:
                issue_comments = self._get(
                    f"{GITHUB_API}/repos/{repo_ref}/issues/{pr_num}/comments",
                    params={"per_page": 100},
                )
            except requests.HTTPError as e:
                print(f"PR poll warning: failed to fetch issue comments for PR #{pr_num}: {e}")
                continue

            for c in issue_comments:
                cid = c["id"]
                if self._state_store.is_seen(repo_ref, pr_num, cid):
                    continue

                if is_first_pr_poll or c["body"].startswith("**["):
                    self._state_store.seed_comment(
                        repo_ref=repo_ref, pr_number=pr_num, comment_id=cid,
                        thread_root_id=cid,
                        author=c["user"]["login"], body=c["body"],
                        created_at=c["created_at"], url=c["html_url"],
                        path="", original_line=None, comment_type="issue",
                    )
                else:
                    self._state_store.add_new_comment(
                        repo_ref=repo_ref, pr_number=pr_num, comment_id=cid,
                        thread_root_id=cid,
                        author=c["user"]["login"], body=c["body"],
                        created_at=c["created_at"], url=c["html_url"],
                        path="", original_line=None, comment_type="issue",
                    )
                    new_comments.append(PRComment(
                        pr_number=pr_num,
                        pr_title=pr_titles[pr_num],
                        comment_id=cid,
                        comment_type="issue",
                        author=c["user"]["login"],
                        body=c["body"],
                        created_at=c["created_at"],
                        url=c["html_url"],
                    ))

        return new_comments, merged_prs

    def get_thread_history(self, repo_ref: str, comment: PRComment) -> list[dict]:
        """Return all prior comments in the same thread, sorted oldest first, excluding the trigger comment."""
        root_id = comment.in_reply_to_id or comment.comment_id

        if comment.comment_type == "review":
            all_comments = self._get(
                f"{GITHUB_API}/repos/{repo_ref}/pulls/comments",
                params={"per_page": 100, "sort": "created", "direction": "asc"},
            )
            thread = [
                c for c in all_comments
                if (c["id"] == root_id or c.get("in_reply_to_id") == root_id)
                and c["id"] != comment.comment_id
            ]
        else:
            all_comments = self._get(
                f"{GITHUB_API}/repos/{repo_ref}/issues/{comment.pr_number}/comments",
                params={"per_page": 100},
            )
            thread = [c for c in all_comments if c["id"] != comment.comment_id]

        return [{"author": c["user"]["login"], "body": c["body"]} for c in thread]

    def get_thread_history_by_root(self, repo_ref: str, pr_number: int, root_id: int) -> list[dict]:
        """Return all comments in a review thread given the root comment ID."""
        all_comments = self._get(
            f"{GITHUB_API}/repos/{repo_ref}/pulls/comments",
            params={"per_page": 100, "sort": "created", "direction": "asc"},
        )
        thread = [
            c for c in all_comments
            if c["id"] == root_id or c.get("in_reply_to_id") == root_id
        ]
        return [{"author": c["user"]["login"], "body": c["body"]} for c in thread]

    def get_pr_title(self, repo_ref: str, pr_number: int) -> str:
        resp = self._session.get(f"{GITHUB_API}/repos/{repo_ref}/pulls/{pr_number}")
        return resp.json().get("title", "") if resp.ok else ""

    def close_linked_issues(self, repo_ref: str, pr: dict) -> list[int]:
        body = pr.get("body") or ""
        pattern = r'(?:closes?|fixes?|resolves?)\s+#(\d+)'
        issue_numbers = [int(m) for m in re.findall(pattern, body, re.IGNORECASE)]
        closed = []
        for num in issue_numbers:
            resp = self._session.patch(
                f"{GITHUB_API}/repos/{repo_ref}/issues/{num}",
                json={"state": "closed"},
            )
            if resp.ok:
                closed.append(num)
                print(f"  Closed issue #{num}")
            else:
                print(f"  Failed to close issue #{num}: {resp.status_code}")
        return closed

    def _get_pr_anchor(self, repo_ref: str, pr_number: int) -> tuple[str, str, int]:
        """Return (commit_sha, path, line) for anchoring a review comment to the PR diff."""
        pr_resp = self._session.get(f"{GITHUB_API}/repos/{repo_ref}/pulls/{pr_number}")
        pr_resp.raise_for_status()
        commit_id = pr_resp.json()["head"]["sha"]

        files_resp = self._session.get(
            f"{GITHUB_API}/repos/{repo_ref}/pulls/{pr_number}/files",
            params={"per_page": 100},
        )
        files_resp.raise_for_status()
        files = files_resp.json()

        for file_data in files:
            if file_data.get("status") == "removed":
                continue
            patch = file_data.get("patch", "")
            if not patch:
                continue
            path = file_data["filename"]
            m = re.search(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', patch)
            line = int(m.group(1)) if m else 1
            return commit_id, path, line

        path = files[0]["filename"] if files else "README.md"
        return commit_id, path, 1

    def reply(self, repo_ref: str, comment: PRComment, body: str,
              is_question: bool = False) -> int:
        """Post a reply to a PR comment. Always replies as a review comment (threaded).
        For issue comments, anchors to the first changed line of the first file.
        Pass is_question=True when the reply is a clarifying question awaiting user input."""
        reply_status = "awaiting_user" if is_question else "resolved"

        if comment.comment_type == "review":
            url = f"{GITHUB_API}/repos/{repo_ref}/pulls/{comment.pr_number}/comments/{comment.comment_id}/replies"
            resp = self._session.post(url, json={"body": body})
            resp.raise_for_status()
            new_id = resp.json()["id"]
            thread_root_id = comment.in_reply_to_id or comment.comment_id
            self._state_store.seed_comment(
                repo_ref=repo_ref, pr_number=comment.pr_number, comment_id=new_id,
                thread_root_id=thread_root_id,
                author="bot", body=body, created_at="",
                url="", path=comment.path, original_line=comment.original_line,
                comment_type="review", status=reply_status,
            )
        else:
            commit_id, path, line = self._get_pr_anchor(repo_ref, comment.pr_number)
            url = f"{GITHUB_API}/repos/{repo_ref}/pulls/{comment.pr_number}/comments"
            resp = self._session.post(url, json={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
                "side": "RIGHT",
            })
            resp.raise_for_status()
            new_id = resp.json()["id"]
            self._state_store.seed_comment(
                repo_ref=repo_ref, pr_number=comment.pr_number, comment_id=new_id,
                thread_root_id=new_id,
                author="bot", body=body, created_at="",
                url="", path=path, original_line=line,
                comment_type="review", anchored_arbitrarily=True, status=reply_status,
            )
        return new_id
