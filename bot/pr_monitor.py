import os
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

    def poll(self, repo_ref: str) -> list[PRComment]:
        """Return new comments since last poll. Call repeatedly; first call seeds state with no output."""
        seen = self._seen_for(repo_ref)
        is_first_poll = not seen["review"] and not seen["issue"]

        try:
            prs = self._open_prs(repo_ref)
        except requests.HTTPError as e:
            raise RuntimeError(f"GitHub API error fetching PRs for {repo_ref}: {e}")

        pr_titles = {pr["number"]: pr["title"] for pr in prs}
        new_comments: list[PRComment] = []

        # Inline review comments across all open PRs
        try:
            review_comments = self._get(
                f"{GITHUB_API}/repos/{repo_ref}/pulls/comments",
                params={"per_page": 100, "sort": "created", "direction": "desc"},
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
                if not is_first_poll:
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
                    if not is_first_poll:
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

        return new_comments

    def reply(self, repo_ref: str, comment: PRComment, body: str) -> None:
        """Post a reply to a PR comment on GitHub."""
        if comment.comment_type == "review":
            url = f"{GITHUB_API}/repos/{repo_ref}/pulls/comments/{comment.comment_id}/replies"
        else:
            url = f"{GITHUB_API}/repos/{repo_ref}/issues/{comment.pr_number}/comments"
        resp = self._session.post(url, json={"body": body})
        resp.raise_for_status()
