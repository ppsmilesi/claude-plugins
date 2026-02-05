---
name: feature-implement
description: Implement a single Linear ticket
disable-model-invocation: true
argument-hint: "[ticket ID or URL]"
---

# Ticket Implementation

Implement a single Linear ticket, using architecture context from its parent project (if any).

Input: $ARGUMENTS (Linear ticket ID, identifier, or URL)

## CRITICAL: Worktree Requirement

**ALWAYS use worktrees. NEVER checkout branches directly in the user's main repository.**

This prevents disrupting the user's working state and allows parallel work on multiple fixes.

---

## Step 1: Load Ticket Context

### Get Ticket Details
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py get-ticket <ticket_id>
```

Extract from the ticket:
- **Summary**: What this task accomplishes
- **Acceptance Criteria**: Testable criteria to satisfy
- **Files to Create/Modify**: Exact paths
- **Patterns to Follow**: References to existing code
- **Notes**: Implementation hints

### Get Project Context (if ticket belongs to a project)

If the ticket is part of a project, fetch the project for architecture context:
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py get-project <project_id>
```

**IMPORTANT**: Read and internalize all available context before implementing.

---

## Step 2: Create Worktree

Create an isolated worktree for this ticket:

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py create-worktree "feature/<ticket-identifier>"
```

### Set Up Environment

Get the worktree ready to run the project. Inspect the repo to understand what's needed (e.g. check for `package.json`, `Makefile`, `docker-compose.yml`, `.tool-versions`, etc.), then:

1. **Copy local config/env files** — Copy any gitignored config files (`.env`, `.*.local.*`, service account keys, etc.) from the main repo into the worktree. **Do NOT read the contents** of these files — just copy them.
2. **Install dependencies** — Run the appropriate install command (`mise install`, `npm install`, `uv sync`, `pip install`, `bundle install`, etc.)
3. **Run setup scripts** — If the project has a setup script or `Makefile` target (e.g. `make setup`, `bin/setup`), run it.
4. **Verify** — Confirm the project builds/compiles before moving on.

---

## Step 3: Implement

Work inside the worktree directory. Execute these phases sequentially using **sub-agents via the Task tool**:

1. **Plan** — Use the **planner** agent: read reference files, create implementation plan
2. **Implement** — Use the **developer** agent: create/modify files, follow patterns
3. **Test** — Use the **tester** agent: write tests, run them
4. **Review** — Use the **reviewer** and **compliance** agents: check quality

Each sub-agent receives:
- **Worktree path**: The isolated directory to work in
- **Ticket context**: Full ticket details (summary, acceptance criteria, files, patterns)
- **Project context**: Architecture overview, tech stack, reference files (if available)

---

## Step 4: Commit

Commit changes with a descriptive message:
```
feat(<scope>): <ticket title>

<summary of changes>

Ticket: <ticket_identifier>
```

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py commit --message "feat(<scope>): <title>

<summary>

Ticket: <ticket_identifier>"
```

Push the branch:
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py push "feature/<ticket-identifier>"
```

---

## Step 5: Create PR

### Determine Base Branch

If this ticket was **blocked by** another ticket, the PR targets that blocker's branch (stacked PR). Otherwise, target `main`.

- **Has blocker**: base = `feature/<blocker-ticket-identifier>`
- **No blocker**: base = `main`

### Merge Base Into Current Branch

Before creating the PR, merge the base branch into the current branch to ensure it includes all upstream changes:

```bash
cd <worktree_path>
git merge <base_branch> --no-edit
```

If there are merge conflicts, resolve them sensibly — prefer the current branch's changes for new code, and the base branch's changes for shared infrastructure. After resolving, commit the merge.

### Create the PR

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py create-pr \
  --title "feat(<scope>): <ticket title>" \
  --body "## Summary
<what this PR does and why>

## Changes
<summary of changes>

## Acceptance Criteria
- [ ] <criteria from ticket>

## Testing
- [ ] Unit tests added
- [ ] Manual testing completed

## Linear Ticket
<ticket_url>" \
  --base "<base_branch>"
```

### Trigger Review

Add a comment on the PR to trigger an automated review:

```bash
gh pr comment <pr_number> --body "@claude"
```

---

## Step 6: Update Linear

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py update-status <ticket_id> --status "In Review"
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py add-comment <ticket_id> --body "PR created: <pr_url>"
```

---

## Step 7: Cleanup

Remove the worktree:
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py remove-worktree "<worktree_path>"
```

---

## Step 8: Summary

Present to the user:
```
## Implementation Complete

### PR Created
<pr_url> (→ main)

### Ticket
<ticket_identifier>: <title>

### Changes
<brief summary of what was implemented>

### Next Steps
1. Review the PR
2. Wait for CI to pass: `/workflow:ci-status`
3. If CI fails: `/workflow:ci-fix`
```

---

## Tool Reference

### Git (`~/.claude/plugins/cache/*/workflow/*/tools/git.py`)

| Command | Description |
|---------|-------------|
| `create-worktree <branch>` | Create worktree for NEW branch |
| `remove-worktree <path>` | Remove worktree after done |
| `commit --message MSG` | Commit changes |
| `push <branch>` | Push to remote |
| `create-pr --title T --body B` | Create PR |
| `changed-files` | List modified files |

### Linear (`~/.claude/plugins/cache/*/workflow/*/tools/linear.py`)

| Command | Description |
|---------|-------------|
| `get-project <id>` | Get project with full description |
| `get-project-tickets <id>` | List all tickets in order |
| `get-ticket <id>` | Get ticket details |
| `update-status <id> --status STATUS` | Update status |
| `add-comment <id> --body "text"` | Add comment |

### GitHub (`~/.claude/plugins/cache/*/workflow/*/tools/github.py`)

| Command | Description |
|---------|-------------|
| `pr-checks <number>` | Check CI status |

---

## Quality Checklist

Before creating PR:
- [ ] All acceptance criteria met
- [ ] Tests written for new functionality
- [ ] Code follows patterns from reference files
- [ ] No markdown files created in codebase
- [ ] Ticket updated with implementation notes
- [ ] Commit message references ticket identifier
