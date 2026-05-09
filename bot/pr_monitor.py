import os
import re
import requests
from dataclasses import dataclass, field
from datetime import datetime


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
    diff_hunk: str = ""  # only for inline review comments
    in_reply_to_id: int = None  # None means this is a thread root


class PRMonitor:
    """Polls GitHub for new PR comments on a given repo."""

    def __init__(self, github_token: str):
        self._token = github_token
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        # {repo_ref: {"review": set_of_seen_ids, "issue": set_of_seen_ids}}
        self._seen: dict[str, dict[str, set]] = {}
        # {repo_ref: set of PR numbers known to be open}
        self._open_pr_numbers: dict[str, set] = {}

    def _seen_for(self, repo_ref: str) -> dict[str, set]:
        if repo_ref not in self._seen:
            self._seen[repo_ref] = {"review": set(), "issue": set()}
        return self._seen[repo_ref]

    def _get(self, url: str, params: dict = None) -> list:
        results = []
        while url:
            resp = self._session.get(url, params=params)
            resp.raise_for_status()
            results.extend(resp.json())
            url = resp.links.get("next", {}).get("url")
            params = None  # params only on first request
        return results

    def _open_prs(self, repo_ref: str) -> list[dict]:
        return self._get(f"{GITHUB_API}/repos/{repo_ref}/pulls", params={"state": "open", "per_page": 100})

    def detect_merged_prs(self, repo_ref: str, current_prs: list[dict]) -> list[dict]:
        """Return PRs that were open last poll but are now merged/closed."""
        current_numbers = {pr["number"] for pr in current_prs}
        known = self._open_pr_numbers.get(repo_ref)

        if known is None:
            # First poll — seed state, nothing to report
            self._open_pr_numbers[repo_ref] = current_numbers
            return []

        merged_numbers = known - current_numbers
        self._open_pr_numbers[repo_ref] = current_numbers

        if not merged_numbers:
            return []

        # Fetch details for each merged/closed PR
        merged = []
        for num in merged_numbers:
            resp = self._session.get(f"{GITHUB_API}/repos/{repo_ref}/pulls/{num}")
            if resp.ok:
                pr = resp.json()
                if pr.get("merged_at"):  # only truly merged, not just closed
                    merged.append(pr)
        return merged

    def poll(self, repo_ref: str) -> tuple[list[PRComment], list[dict]]:
        """Return (new_comments, merged_prs) since last poll. First call seeds state with no output."""
        seen = self._seen_for(repo_ref)
        is_first_poll = not seen["review"] and not seen["issue"]

        try:
            prs = self._open_prs(repo_ref)
        except requests.HTTPError as e:
            raise RuntimeError(f"GitHub API error fetching PRs for {repo_ref}: {e}")

        merged_prs = self.detect_merged_prs(repo_ref, prs)

        pr_titles = {pr["number"]: pr["title"] for pr in prs}
        new_comments: list[PRComment] = []

        # Inline review comments across all open PRs
        try:
            review_comments = self._get(
                f"{GITHUB_API}/repos/{repo_ref}/pulls/comments",
                params={"per_page": 100, "sort": "created", "direction": "asc"},
            )
        except requests.HTTPError:
            review_comments = []

        for c in review_comments:
            cid = c["id"]
            pr_num = c["pull_request_url"].split("/")[-1]
            pr_num = int(pr_num)

            if pr_num not in pr_titles:
                continue  # skip closed PRs
            if cid not in seen["review"]:
                seen["review"].add(cid)
                if not is_first_poll and not c["body"].startswith("**["):
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
                    ))

        # General issue comments on each open PR
        for pr in prs:
            pr_num = pr["number"]
            try:
                issue_comments = self._get(
                    f"{GITHUB_API}/repos/{repo_ref}/issues/{pr_num}/comments",
                    params={"per_page": 100},
                )
            except requests.HTTPError:
                continue

            for c in issue_comments:
                cid = c["id"]
                if cid not in seen["issue"]:
                    seen["issue"].add(cid)
                    if not is_first_poll and not c["body"].startswith("**["):
                        new_comments.append(PRComment(
                            pr_number=pr_num,
                            pr_title=pr_titles[pr_num],
                            comment_id=cid,
                            comment_type="issue",
                            author=c["user"]["login"],
                            body=c["body"],
                            created_at=c["created_at"],
                            url=c["html_url"],
                            in_reply_to_id=c.get("in_reply_to_id"),
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
            # Issue comments have no threading; return all prior comments in the PR
            thread = [c for c in all_comments if c["id"] != comment.comment_id]

        return [{"author": c["user"]["login"], "body": c["body"]} for c in thread]

    def close_linked_issues(self, repo_ref: str, pr: dict) -> list[int]:
        """Close issues referenced in PR body with Closes/Fixes/Resolves. Returns closed issue numbers."""
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

    def reply(self, repo_ref: str, comment: PRComment, body: str) -> int:
        """Post a reply to a PR comment on GitHub. Returns the new comment ID."""
        if comment.comment_type == "review":
            url = f"{GITHUB_API}/repos/{repo_ref}/pulls/{comment.pr_number}/comments/{comment.comment_id}/replies"
        else:
            url = f"{GITHUB_API}/repos/{repo_ref}/issues/{comment.pr_number}/comments"
        resp = self._session.post(url, json={"body": body})
        resp.raise_for_status()
        new_id = resp.json()["id"]
        # Mark our own reply as seen so the next poll doesn't re-process it
        seen = self._seen_for(repo_ref)
        seen["review" if comment.comment_type == "review" else "issue"].add(new_id)
        return new_id
