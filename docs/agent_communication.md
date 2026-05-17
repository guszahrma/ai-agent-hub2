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
        DelegateCode(["Delegate code fix\nto CodeEditor"])
        DelegateReview(["Delegate review\nto CodeReviewer"])
        DelegateIssue(["Delegate issue\nto IssueManager"])
        DelegateArch(["Delegate design\nto Architect / RE"])
        DelegateJeeves(["Delegate task\nto Jeeves"])
    end

    subgraph InProcessAgents["In-process Agents (Hub Bot)"]
        GitAgent(["GitAgent\ngit operations"])
        CodeEditor(["CodeEditor\nwrite + commit + push"])
        CodeReviewer(["CodeReviewer\npost inline findings"])
        IssueManager(["IssueManager\ncreate / close issues"])
        Architect(["Architect /\nRequirementsEngineer"])
    end

    subgraph JeevesActions["Jeeves (session-triggered)"]
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
    DelegateCode --> CodeEditor
    DelegateReview --> CodeReviewer
    DelegateIssue --> IssueManager
    DelegateArch --> Architect
    GitAgent -- "result" --> ScrumMaster
    CodeEditor -- "[code_editor] → [ScrumMaster]" --> PR
    CodeReviewer -- "inline findings" --> PR
    IssueManager -- "opens/closes issue" --> Issues
    DelegateJeeves -- "posts in PR thread" --> PR

    %% Jeeves picks up task
    PR -- "PO points Jeeves at task" --> JeevesActions
    CodeChange --> CommitPush
    CommitPush -- "[Jeeves] → [ScrumMaster]" --> PR
```

## Current state

```mermaid
sequenceDiagram
    actor PO as Product Owner
    participant GH as GitHub PR
    participant Bot as Hub Bot
    participant SS as State Store (disk)
    participant SM as ScrumMaster
    participant GA as GitAgent
    participant CR as CodeReviewer
    participant CE as CodeEditor
    participant IM as IssueManager
    participant AR as Architect / RE
    actor JE as Jeeves

    PO->>GH: posts PR comment

    loop every 60s
        Bot->>GH: poll for new comments
        GH-->>Bot: new comment found
        Bot->>SS: status = "delegated_to_scrum_master"
    end

    Bot->>SM: handle_pr_comment()

    alt needs git info
        SM->>GA: delegate_to_git_agent() [tool call]
        GA-->>SM: git result
    end

    alt code review requested
        SM->>CR: delegate_to_code_reviewer() [tool call]
        CR->>GH: posts inline findings
    end

    SM->>GH: reply to_po in thread
    GH-->>PO: notified
    Bot->>SS: status = "pending" or "resolved"

    opt code fix needed
        SM->>GH: [ScrumMaster] → [CodeEditor]: task
        Bot->>CE: dispatch execute()
        CE->>CE: fetch PR diff + read file
        CE->>GH: commits fix, pushes
        CE->>GH: [code_editor] → [ScrumMaster]: Applied fix in [sha]
        Bot->>SM: handle_pr_comment() [inline, no poll round-trip]
        SM->>CR: delegate_to_code_reviewer() [verify fix]
        CR->>GH: posts updated findings
        SM->>GH: reply to_po
    end

    opt issue management
        SM->>GH: [ScrumMaster] → [IssueManager]: task
        Bot->>IM: dispatch execute()
        IM->>GH: creates / closes issue
        IM->>GH: [issue_manager] → [ScrumMaster]: done
        Bot->>SM: handle_pr_comment() [inline]
        SM->>GH: reply to_po "Tracked as #N"
    end

    opt Jeeves needed
        SM->>GH: [ScrumMaster] → [Jeeves]: task
        note over GH,JE: Jeeves acts when PO opens a session
        JE->>GH: commits fix
        JE->>GH: [Jeeves] → [ScrumMaster]: done + sha
        Bot->>SM: handle_pr_comment() [next poll]
        SM->>GH: reply to_po
    end
```

## Communication paths

| From | To | Mechanism | Reliable? |
|---|---|---|---|
| Product Owner | ScrumMaster | PR comment → bot poll | ✓ (with state persistence) |
| Product Owner | ScrumMaster | Discord message → bot | ✓ |
| ScrumMaster | Product Owner | PR comment reply (`to_po`) | ✓ |
| ScrumMaster | GitAgent | In-process tool call | ✓ |
| ScrumMaster | CodeReviewer | In-process tool call (`delegate_to_code_reviewer`) | ✓ |
| ScrumMaster | CodeEditor | In-process dispatch via `to_agents` | ✓ |
| ScrumMaster | IssueManager | In-process dispatch via `to_agents` | ✓ |
| ScrumMaster | Architect | In-process dispatch via `to_agents` | ✓ |
| ScrumMaster | RequirementsEngineer | In-process dispatch via `to_agents` | ✓ |
| CodeEditor | ScrumMaster | `**[code_editor] → [ScrumMaster]:**` comment → bot re-invokes ScrumMaster inline | ✓ |
| Any agent | ScrumMaster | `**[agent] → [ScrumMaster]:**` comment → bot re-invokes ScrumMaster inline | ✓ |
| GitAgent | ScrumMaster | Return value from tool call | ✓ |
| Jeeves | ScrumMaster | `**[Jeeves] → [ScrumMaster]:**` PR comment | ✓ (picked up on next poll) |
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
