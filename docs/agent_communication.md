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
| Hub Bot | State Store | Read/write on every status change | ✓ (atomic writes) |

## Proposed improvements

1. **Rename Discord Bot → Hub Bot** — reflects that it polls both Discord and GitHub
2. **Persistent state store** — replace in-memory `_seen` set with a disk-backed store tracking full comment status (`received`, `delegated_jeeves`, `delegated_git`, `awaiting_po`, `issue_created`, `resolved`)
3. **`jeeves_inbox/`** — ScrumMaster writes task files; Jeeves checks at session start
4. **Discord ping on Jeeves delegation** — notifies PO to open Claude Code
5. **ScrumMaster reports status back to bot** — bot is the single owner of state; agents report up the chain
