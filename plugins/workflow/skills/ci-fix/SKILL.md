---
name: ci-fix
description: Auto-fix failing CI tests on PRs
disable-model-invocation: true
argument-hint: "[PR number]"
---

# CI Auto-Fix

Input: $ARGUMENTS (optional PR number, otherwise fixes all failing)

## CRITICAL: Worktree Requirement

**ALWAYS use worktrees. NEVER checkout branches directly in the user's main repository.**

This prevents disrupting the user's working state and allows parallel work on multiple fixes.

---

## Steps

### 1. Get Failing PRs
```bash
python plugins/workflow/tools/github.py all-prs-status
```
Filter for PRs with `ci_status: "failing"`

### 2. For Each Failing PR

#### 2.1 Get Failure Details
```bash
# Get the branch name
python plugins/workflow/tools/github.py pr-branch <pr_number> --repo <owner/repo>

# Get detailed failure logs
python plugins/workflow/tools/github.py ci-logs <pr_number> --repo <owner/repo>
```

#### 2.2 Create Worktree for the Existing Branch

**MANDATORY**: Use `checkout-worktree` (not `create-worktree`) for existing PR branches:

```bash
# Navigate to the repository first
cd <repo_path>

# Create worktree for the existing branch
python plugins/workflow/tools/git.py checkout-worktree "<branch_name>"
```

This will:
- Fetch the branch from origin
- Create an isolated worktree at `../.worktrees/<repo>/ci-fix-<branch>`
- Return the worktree path in JSON format

**Use the returned worktree path for all subsequent operations.**

#### 2.3 Analyze and Fix

Work in the worktree directory:
```bash
cd <worktree_path>
```

Use the **debugger** agent to:
1. Analyze the CI failure logs
2. Identify the root cause
3. Implement the fix

#### 2.4 Verify Fix

Use the **tester** agent to run the failing tests locally if possible.

#### 2.5 Commit and Push

From the worktree directory:
```bash
# Commit the fix
python plugins/workflow/tools/git.py commit --message "fix: resolve CI failure - <description>"

# Push to the PR branch
python plugins/workflow/tools/git.py push "<branch_name>"
```

#### 2.6 Cleanup Worktree

After the fix is pushed:
```bash
python plugins/workflow/tools/git.py remove-worktree "<worktree_path>"
```

### 3. Monitor

After pushing, check if CI passes:
```bash
python plugins/workflow/tools/github.py pr-checks <pr_number> --repo <owner/repo>
```

---

## Tool Reference

### Git (`plugins/workflow/tools/git.py`)

| Command | Description |
|---------|-------------|
| `checkout-worktree <branch>` | **Use this for CI fixes** - Creates worktree for existing branch |
| `create-worktree <branch>` | Creates worktree for NEW branch (not for CI fixes) |
| `remove-worktree <path>` | Remove a worktree after done |
| `list-worktrees` | List all active worktrees |
| `commit --message MSG` | Stage and commit all changes |
| `push <branch>` | Push branch to remote |

### GitHub (`plugins/workflow/tools/github.py`)

| Command | Description |
|---------|-------------|
| `all-prs-status [--repo REPO]` | Get all PRs with CI status |
| `pr-branch <number> [--repo REPO]` | Get branch name for PR |
| `ci-logs <number> [--repo REPO]` | Get failure logs |
| `pr-checks <number> [--repo REPO]` | Check current CI status |
| `failed-checks <number> [--repo REPO]` | Get only failed checks |

---

## Example Workflow

```bash
# 1. Find failing PRs
python plugins/workflow/tools/github.py all-prs-status

# 2. Get branch name for PR #123 in ouihelp/api
python plugins/workflow/tools/github.py pr-branch 123 --repo ouihelp/api
# Output: my-feature-branch

# 3. Get failure logs
python plugins/workflow/tools/github.py ci-logs 123 --repo ouihelp/api

# 4. Create worktree (from the repo directory)
cd ~/Repos/api
python plugins/workflow/tools/git.py checkout-worktree "my-feature-branch"
# Output: {"path": "/Users/.../worktrees/api/ci-fix-my-feature-branch", "branch": "my-feature-branch"}

# 5. Work in worktree
cd /Users/.../worktrees/api/ci-fix-my-feature-branch
# ... make fixes ...

# 6. Commit and push
python plugins/workflow/tools/git.py commit --message "fix: resolve type error in handler"
python plugins/workflow/tools/git.py push "my-feature-branch"

# 7. Check CI status
python plugins/workflow/tools/github.py pr-checks 123 --repo ouihelp/api
```
