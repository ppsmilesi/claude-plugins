---
name: feature-implement
description: Implement a feature from a Linear project
disable-model-invocation: true
argument-hint: "[project ID]"
---

# Feature Implementation

Implement all tickets from a Linear project, using the architecture context stored in the project description.

Input: $ARGUMENTS (Linear project ID, name, or URL)

## CRITICAL: Worktree Requirement

**ALWAYS use worktrees. NEVER checkout branches directly in the user's main repository.**

This prevents disrupting the user's working state and allows parallel work on multiple fixes.

---

## Step 1: Load Project Context

### Get Project Details
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py get-project <project_id>
```

The project description contains critical context from `/workflow:feature-plan`:
- **Original Requirements**: What the feature should do
- **Architecture Overview**: How it should be built
- **Tech Stack Context**: Framework, libraries, patterns
- **Key Decisions**: Why certain choices were made
- **Reference Files**: Existing code to follow as examples
- **Out of Scope**: What NOT to implement

**IMPORTANT**: Read and internalize this context before implementing any ticket.

### Get All Tickets
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py get-project-tickets <project_id>
```

---

## Step 2: Group Tickets by Tier

Parse the ticket descriptions to extract tier information (from the `### Tier` section in each ticket's description). Group tickets into tiers:

- **Tier 0**: Tickets with no dependencies / no blockers
- **Tier N**: Tickets whose blockers are all in tiers < N

Build a mapping: `tier_number → [list of tickets]`

Identify the total number of tiers and the tickets in each.

---

## Step 3: Process Each Tier

Process tiers sequentially (0, 1, 2...). Within each tier, process all tickets **in parallel**.

### 3a. Create Worktrees in Parallel

For each ticket in the current tier, create an isolated worktree:

```bash
# Tier 0: branch from origin/main
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py create-worktree "feature/<project-slug>/tier-<N>/<ticket-identifier>"

# Tier N (N>0): branch from the previous tier's integration branch
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py create-worktree "feature/<project-slug>/tier-<N>/<ticket-identifier>" --start-point "feature/<project-slug>/tier-<N-1>"
```

### 3b. Launch Sub-Agents in Parallel

Use the **Task tool** to launch one sub-agent per ticket **in a single message** (parallel execution). Each agent receives:

- **Worktree path**: The isolated directory to work in
- **Ticket context**: Full ticket details (summary, acceptance criteria, files, patterns)
- **Project context**: Architecture overview, tech stack, reference files from the project description

Each sub-agent independently executes:

1. **Plan** — Use the **planner** agent: read reference files, create implementation plan
2. **Implement** — Use the **developer** agent: create/modify files, follow patterns
3. **Test** — Use the **tester** agent: write tests, run them
4. **Review** — Use the **reviewer** and **compliance** agents: check quality
5. **Commit** — Commit changes with message:
   ```
   feat(<scope>): <ticket title>

   <summary of changes>

   Ticket: <ticket_identifier>
   ```
6. **Update Linear** — Add implementation comment to the ticket

### 3c. Create Tier Integration Branch

After all sub-agents in the tier complete:

1. Create the tier integration branch:
   ```bash
   # Tier 0: from origin/main
   python ~/.claude/plugins/cache/*/workflow/*/tools/git.py create-worktree "feature/<project-slug>/tier-<N>"

   # Tier N>0: from previous tier
   python ~/.claude/plugins/cache/*/workflow/*/tools/git.py create-worktree "feature/<project-slug>/tier-<N>" --start-point "feature/<project-slug>/tier-<N-1>"
   ```

2. Merge each ticket worktree into the integration branch:
   ```bash
   cd <tier_integration_worktree_path>
   git merge "feature/<project-slug>/tier-<N>/<ticket-identifier>" --no-edit
   ```
   Repeat for each ticket in the tier.

3. Push the integration branch:
   ```bash
   python ~/.claude/plugins/cache/*/workflow/*/tools/git.py push "feature/<project-slug>/tier-<N>"
   ```

### 3d. Create Stacked PR for the Tier

Create a PR for the tier's integration branch targeting the previous tier (or `main` for tier 0):

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py create-pr \
  --title "feat(<scope>): <feature name> - Tier <N>" \
  --body "## Summary
<architecture overview from project>

## Tier <N> Tickets
- <TICKET-1>: <title>
- <TICKET-2>: <title>

## Changes
<summary of changes in this tier>

## Stacked PR
- Base: <target branch (main or previous tier branch)>
- This is tier <N> of <total tiers>

## Testing
- [ ] Unit tests added
- [ ] Manual testing completed

## Linear Project
<project_url>" \
  --base "<target_branch>"
```

**Stacked PR targeting:**
- Tier 0 PR → targets `main`
- Tier 1 PR → targets `feature/<project-slug>/tier-0`
- Tier N PR → targets `feature/<project-slug>/tier-<N-1>`

### 3e. Update Linear Tickets

For each ticket in the tier:
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py update-status <ticket_id> --status "In Review"
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py add-comment <ticket_id> --body "PR created: <pr_url>"
```

Then proceed to the next tier.

---

## Step 4: Cleanup

After all tiers are processed, remove worktrees:
```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/git.py remove-worktree "<worktree_path>"
```

---

## Step 5: Summary

Present to the user:
```
## Implementation Complete

### Stacked PRs Created
- Tier 0: <pr_url_0> (→ main)
- Tier 1: <pr_url_1> (→ tier-0)
- ...

### Tickets Implemented
- <TICKET-1>: <title> (Tier 0)
- <TICKET-2>: <title> (Tier 0)
- <TICKET-3>: <title> (Tier 1)
- ...

### Next Steps
1. Review PRs bottom-up: merge Tier 0 first, then Tier 1, etc.
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
| `block-ticket <id> --blocked-by <id>` | Set blocking relation |

### GitHub (`~/.claude/plugins/cache/*/workflow/*/tools/github.py`)

| Command | Description |
|---------|-------------|
| `pr-checks <number>` | Check CI status |

---

## Quality Checklist

Before creating PR:
- [ ] All acceptance criteria met for each ticket
- [ ] Tests written for new functionality
- [ ] Code follows patterns from reference files
- [ ] No markdown files created in codebase
- [ ] All tickets updated with implementation notes
- [ ] Commit messages reference ticket identifiers
