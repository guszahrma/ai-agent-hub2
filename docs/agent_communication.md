# Agent Communication — Use Case Diagram

```mermaid
graph TB
    PO(["👤 Product Owner"])
    Jeeves(["👤 Jeeves\n(Claude Code)"])

    subgraph GitHub["🌐 GitHub"]
        PR(["Pull Request\nthread"])
        Issues(["Issues /\nProject board"])
        Inbox(["jeeves_inbox/\ntask files"])
    end

    subgraph Bot["Discord Bot (persistent process)"]
        Monitor(["Monitor PR\ncomments"])
        Route(["Route comment\nto ScrumMaster"])
        PersistState(["Persist seen-comment\nstate to disk"])
    end

    subgraph ScrumMaster["ScrumMaster Agent"]
        RespondPO(["Respond to PO\nin PR thread"])
        DelegateGit(["Delegate git\ntask to GitAgent"])
        DelegateJeeves(["Delegate task\nto Jeeves"])
        CreateIssue(["Create\nGitHub issue"])
    end

    subgraph GitAgent["GitAgent"]
        RunGit(["Execute local\ngit operations"])
    end

    subgraph JeevesActions["Jeeves Actions (session-triggered)"]
        CheckInbox(["Check\njeeves_inbox/"])
        CodeChange(["Implement code\nchanges"])
        CommitPush(["Commit & push\nto branch"])
    end

    %% PO interactions
    PO -- "posts PR comment" --> PR
    PO -- "opens Claude Code" --> JeevesActions

    %% Bot monitors GitHub
    PR -- "new comment" --> Monitor
    Monitor --> Route
    Monitor --> PersistState
    PersistState -- "survives restart" --> Monitor

    %% ScrumMaster handles comment
    Route --> ScrumMaster
    RespondPO -- "posts reply" --> PR
    DelegateGit --> GitAgent
    RunGit -- "returns result" --> ScrumMaster
    DelegateJeeves -- "writes task file" --> Inbox
    DelegateJeeves -- "posts Discord ping" --> PO
    CreateIssue -- "opens issue" --> Issues

    %% Jeeves picks up task
    Inbox --> CheckInbox
    CheckInbox --> CodeChange
    CodeChange --> CommitPush
    CommitPush -- "posts commit to PR" --> PR
```

## Current state

```mermaid
sequenceDiagram
    actor PO as Product Owner
    participant GH as GitHub PR
    participant Bot as Discord Bot
    participant SM as ScrumMaster
    participant GA as GitAgent
    actor JE as Jeeves

    PO->>GH: posts PR comment

    loop every 60s
        Bot->>GH: poll for new comments
        GH-->>Bot: new comment found
        note over Bot: ⚠️ all comments re-seeded as seen on restart
    end

    Bot->>SM: handle_pr_comment()

    alt needs git info
        SM->>GA: delegate_to_git_agent()
        GA-->>SM: git result
    end

    SM->>GH: reply to_po in thread
    GH-->>PO: notified

    opt task for Jeeves
        SM->>GH: posts [Jeeves] comment in thread
        note over GH,JE: ⚠️ no delivery — Jeeves never sees this
        note over JE: only acts if PO manually\npoints it out
    end

    opt out of scope
        SM->>GH: reply "Tracked as #N"
        SM->>GH: create new issue #N
    end
```

## Proposed state

```mermaid
sequenceDiagram
    actor PO as Product Owner
    participant GH as GitHub PR
    participant DC as Discord Channel
    participant Bot as Hub Bot
    participant SS as State Store (disk)
    participant SM as ScrumMaster
    participant GA as GitAgent
    participant JI as jeeves_inbox/
    actor JE as Jeeves

    PO->>GH: posts PR comment

    loop every 60s
        Bot->>GH: poll for new comments
        GH-->>Bot: new comment found
        Bot->>SS: status = "received"
    end

    Bot->>SM: handle_pr_comment()

    alt needs git info
        SM->>GA: delegate_to_git_agent()
        GA-->>SM: git result
        SM-->>Bot: status = "delegated_git / resolved"
        Bot->>SS: update state
    end

    SM->>GH: reply to_po in thread
    GH-->>PO: notified
    SM-->>Bot: status = "awaiting_po"
    Bot->>SS: update state

    opt task for Jeeves
        SM->>JI: write task file
        SM->>DC: ping — Jeeves has a task in PR #N
        SM-->>Bot: status = "delegated_jeeves"
        Bot->>SS: update state
        DC-->>PO: sees ping, opens Claude Code
        PO->>JE: opens session
        JE->>JI: check inbox at session start
        JI-->>JE: pending task
        JE->>GH: commits fix, replies in thread
        JE->>SM: reports completion
        SM-->>Bot: status = "resolved"
        Bot->>SS: update state
        GH-->>PO: notified
    end

    opt out of scope
        SM->>GH: reply "Tracked as #N"
        SM->>GH: create new issue #N
        SM-->>Bot: status = "issue_created / resolved"
        Bot->>SS: update state
    end
```

## Communication paths

| From | To | Mechanism | Reliable? |
|---|---|---|---|
| Product Owner | ScrumMaster | PR comment → bot poll | ✓ (with state persistence) |
| Product Owner | ScrumMaster | Discord message → bot | ✓ |
| ScrumMaster | Product Owner | PR comment reply (to_po) | ✓ |
| ScrumMaster | GitAgent | In-process tool use | ✓ |
| ScrumMaster | Jeeves | `jeeves_inbox/` file + Discord ping | ✓ |
| ScrumMaster | Hub Bot | Status report (after each action) | ✓ |
| GitAgent | ScrumMaster | Return value from tool call | ✓ |
| Jeeves | ScrumMaster | Report completion via PR comment | ✓ |
| Hub Bot | State Store | Sole writer — reads and writes on every status change | ✓ (atomic writes) |

## State store ownership

Hub Bot is the **sole writer** of `bot/state/comment_state_PR[ID].json`. No agent writes to it directly.

Agents report status changes up the chain:

```
Jeeves → ScrumMaster → Hub Bot → State Store
```

This eliminates concurrent write risk and makes Hub Bot the single source of truth for all comment and delegation state.

### Comment status lifecycle

Each comment in the state store has a `status` field updated exclusively by Hub Bot:

| status | set when |
|---|---|
| `new` | Hub Bot first sees the comment |
| `delegated_to_scrum_master` | Hub Bot forwards the comment to ScrumMaster |
| `pending` | ScrumMaster reports back that it has created a delegation — work is ongoing |
| `resolved` | Hub Bot derives this when all delegation items on the comment are `resolved` or `superseded` |

When a comment has no delegations, Hub Bot sets `resolved_by` to the ID of the comment that constitutes the resolution (e.g. the ScrumMaster reply). Comments that are themselves responses (ScrumMaster replies, Jeeves completions) are marked `resolved` immediately when posted — they require no further action.

Thread `status` is also derived: Hub Bot sets it to `resolved` when all comments in the thread are `resolved`.

### Delegation status lifecycle

Each delegation item has a unique `id` and its own `status`, updated exclusively by Hub Bot on behalf of the reporting agent. Agents always include the comment ID and delegation ID when reporting back so Hub Bot knows exactly what to update.

| status | set when |
|---|---|
| `pending` | ScrumMaster reports the delegation was created |
| `in_progress` | Jeeves reports to ScrumMaster that work has started; ScrumMaster relays to Hub Bot |
| `resolved` | Jeeves reports completion with commit SHA; ScrumMaster relays to Hub Bot |
| `superseded` | A later re-delegation replaces this one |

## Proposed improvements

1. **Rename Discord Bot → Hub Bot** — reflects that it polls both Discord and GitHub
2. **Persistent state store** — replace in-memory `_seen` set with `bot/state/comment_state_PR[ID].json`, tracking per-comment and per-delegation status
3. **Hub Bot as sole writer** — all agents report status up the chain; Hub Bot is the only process that writes to the state store
4. **`jeeves_inbox/`** — ScrumMaster writes task files; Jeeves checks at session start
5. **Discord ping on Jeeves delegation** — notifies PO to open Claude Code
