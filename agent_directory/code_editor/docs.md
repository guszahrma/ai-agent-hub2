# CodeEditor Agent

## Purpose
The CodeEditor applies targeted, scoped code fixes to a repository. It is invoked by the ScrumMaster when a PR comment results in an action that requires a specific code change. It produces a precise plan of what to change and how, which Jeeves (or an automated pipeline) then applies.

## Responsibilities
- Interpret a specific, bounded fix task
- Produce the corrected file content or a unified diff
- Provide a commit message for the change
- Refuse ambiguous tasks and list the ambiguity explicitly

## Interaction model
CodeEditor is not Discord-facing. It is called by the ScrumMaster when a PR comment is routed as "Fix in current PR." The ScrumMaster delegates the fix to Jeeves (who may invoke CodeEditor for planning) or directly to CodeEditor if the change is fully automated.

**Addressing syntax in a PR comment:**
```
**[ScrumMaster] → [Jeeves/CodeEditor]:** Fix `_path` in state_store.py to include repo_ref in the filename.
```

## Output format
`plan_change()` returns a structured text response with three sections: File, Change, and Commit message.

## Config
```yaml
model: claude-sonnet-4-6
max_tokens: 4096
git_name: CodeEditor
git_email: code-editor@ai-agent-hub2
```
