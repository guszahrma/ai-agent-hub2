# Auth Setup

## SSH (required for push/pull)

Agents use SSH for git remote operations. No credentials are stored in this repo.

Set up SSH for GitHub once on the host machine:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# Add ~/.ssh/id_ed25519.pub to GitHub → Settings → SSH Keys
ssh -T git@github.com  # verify
```

Ensure your remotes use SSH, not HTTPS:

```bash
git remote set-url origin git@github.com:guszahrma/your-repo.git
```

## Safety guardrails

Built into `tools/git_tools.py`:

| Operation | Behaviour |
|---|---|
| Push to `main` / `master` | Blocked unless explicitly confirmed |
| Force push | Not implemented — use CLI directly if truly needed |
| Auth failure | Clear error message with SSH setup hint |

## Adding a protected branch

Edit `PROTECTED_BRANCHES` in [tools/git_tools.py](../tools/git_tools.py).
