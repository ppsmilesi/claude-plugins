---
description: Implement a feature from a Linear project
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
python plugins/workflow/tools/linear.py get-project <project_id>
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
python plugins/workflow/tools/linear.py get-project-tickets <project_id>
```

Tickets are ordered by dependency. Implement them in order.

---

## Step 2: Create Worktree (FIRST)

**Before starting any ticket**, create an isolated worktree:

```bash
python plugins/workflow/tools/git.py create-worktree "feature/<project-slug>"
```

This returns the worktree path. **All subsequent work must be done in this directory.**

```bash
cd <worktree_path>
```

---

## Step 3: For Each Ticket

### 3.1 Read Ticket Context
```bash
python plugins/workflow/tools/linear.py get-ticket <ticket_id>
```

Each ticket contains:
- **Summary**: What to accomplish
- **Acceptance Criteria**: Definition of done
- **Files to Create**: Exact paths
- **Files to Modify**: Exact paths with changes
- **Patterns to Follow**: Reference files to copy from
- **Dependencies**: Prerequisites
- **Notes**: Implementation hints

### 3.2 Update Status
```bash
python plugins/workflow/tools/linear.py update-status <ticket_id> --status "In Progress"
```

### 3.3 Implementation

Work in the worktree directory for all file operations.

#### Planning Phase
Use the **planner** agent with the ticket context:
- Read the reference files mentioned in "Patterns to Follow"
- Understand the existing code patterns
- Create a step-by-step implementation plan

#### Development Phase
Use the **developer** agent to:
- Create files listed in "Files to Create"
- Modify files listed in "Files to Modify"
- Follow patterns from the reference files
- Check off acceptance criteria as you go

#### Testing Phase
Use the **tester** agent to:
- Write tests for the new functionality
- Follow existing test patterns in the codebase
- Ensure all acceptance criteria are testable

#### Review Phase
Use the **reviewer** and **compliance** agents to:
- Check code quality and security
- Verify project conventions are followed

### 3.4 Commit Changes
```bash
python plugins/workflow/tools/git.py commit --message "feat(<scope>): <ticket title>

<summary of changes>

Ticket: <ticket_identifier>"
```

### 3.5 Update Ticket
```bash
python plugins/workflow/tools/linear.py add-comment <ticket_id> --body "Implementation complete.

## Changes
- <file1>: <what changed>
- <file2>: <what changed>

## Acceptance Criteria
- [x] <criterion 1>
- [x] <criterion 2>"
```

---

## Step 4: Create PR (after all tickets)

### Push Branch
```bash
python plugins/workflow/tools/git.py push "feature/<project-slug>"
```

### Create Pull Request
```bash
python plugins/workflow/tools/git.py create-pr \
  --title "feat: <feature name>" \
  --body "## Summary
<architecture overview from project>

## Tickets Implemented
- <TICKET-1>: <title>
- <TICKET-2>: <title>

## Changes
<summary of all changes>

## Testing
- [ ] Unit tests added
- [ ] Manual testing completed

## Linear Project
<project_url>"
```

### Update All Tickets
```bash
python plugins/workflow/tools/linear.py update-status <ticket_id> --status "In Review"
python plugins/workflow/tools/linear.py add-comment <ticket_id> --body "PR created: <pr_url>"
```

---

## Step 5: Cleanup (Optional)

After PR is merged:
```bash
python plugins/workflow/tools/git.py remove-worktree "<worktree_path>"
```

---

## Step 6: Summary

Present to the user:
```
## Implementation Complete

### PR Created
<pr_url>

### Tickets Implemented
- <TICKET-1>: <title> ✓
- <TICKET-2>: <title> ✓

### Files Changed
- <file1>
- <file2>

### Next Steps
1. Wait for CI to pass: `/workflow:ci-status`
2. If CI fails: `/workflow:ci-fix`
3. Request review
```

---

## Tool Reference

### Git (`plugins/workflow/tools/git.py`)

| Command | Description |
|---------|-------------|
| `create-worktree <branch>` | Create worktree for NEW branch |
| `remove-worktree <path>` | Remove worktree after done |
| `commit --message MSG` | Commit changes |
| `push <branch>` | Push to remote |
| `create-pr --title T --body B` | Create PR |
| `changed-files` | List modified files |

### Linear (`plugins/workflow/tools/linear.py`)

| Command | Description |
|---------|-------------|
| `get-project <id>` | Get project with full description |
| `get-project-tickets <id>` | List all tickets in order |
| `get-ticket <id>` | Get ticket details |
| `update-status <id> --status STATUS` | Update status |
| `add-comment <id> --body "text"` | Add comment |

### GitHub (`plugins/workflow/tools/github.py`)

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
