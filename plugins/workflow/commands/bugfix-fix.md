---
description: Implement bug fix from investigated Linear ticket
---

# Bug Fix Implementation

Input: $ARGUMENTS (Linear ticket ID)

## CRITICAL: Worktree Requirement

**ALWAYS use worktrees. NEVER checkout branches directly in the user's main repository.**

This prevents disrupting the user's working state and allows parallel work on multiple fixes.

---

## Step 1: Fetch Investigation

Get ticket and check for investigation comments:
```bash
python plugins/workflow/tools/linear.py get-ticket <ticket_id>
```

## Step 2: Create Worktree

Create an isolated worktree for the new fix branch:
```bash
python plugins/workflow/tools/git.py create-worktree "fix/<identifier>-<slug>"
```

This returns the worktree path. **All subsequent work must be done in this directory.**

```bash
cd <worktree_path>
```

## Step 3: Implement Fix

Use the **debugger** agent to implement the minimal fix.

Work in the worktree directory for all file operations.

## Step 4: Regression Test

Use the **tester** agent to create a regression test.

## Step 5: Review & PR

Use **reviewer** and **compliance** agents, then from the worktree directory:
```bash
# Commit the fix
python plugins/workflow/tools/git.py commit --message "fix: <description>"

# Push branch
python plugins/workflow/tools/git.py push "fix/<identifier>-<slug>"

# Create PR
python plugins/workflow/tools/git.py create-pr --title "fix: <title>" --body "Fixes <ticket_id>

## Changes
- <change 1>
- <change 2>

## Testing
- Added regression test"

# Update Linear ticket
python plugins/workflow/tools/linear.py update-status <ticket_id> --status "In Review"
python plugins/workflow/tools/linear.py add-comment <ticket_id> --body "PR created: <pr_url>"
```

## Step 6: Cleanup (Optional)

After PR is merged:
```bash
python plugins/workflow/tools/git.py remove-worktree "<worktree_path>"
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

### Linear (`plugins/workflow/tools/linear.py`)

| Command | Description |
|---------|-------------|
| `get-ticket <id>` | Get ticket details |
| `update-status <id> --status STATUS` | Update status |
| `add-comment <id> --body "text"` | Add comment |
