---
description: Check CI status for all open PRs
---

# CI Status Check

## Steps

### 1. Get All Open PRs with Status
```bash
python plugins/workflow/tools/github.py all-prs-status
```

This returns a JSON array with each PR's:
- number, title, url
- branch, base_branch
- ci_status: "passing", "failing", "pending", "unknown"
- checks: list of individual check results

### 2. Display Results
Present a table showing:
| PR | Title | Branch | CI Status | Failed Checks |
|----|-------|--------|-----------|---------------|

### 3. For Failing PRs
Offer to:
- Get detailed CI logs: `python plugins/workflow/tools/github.py ci-logs <pr_number>`
- Auto-fix with `/workflow:ci-fix`

## Tool Reference

### GitHub (`plugins/workflow/tools/github.py`)
- `my-prs [--repo REPO]` - List my open PRs
- `all-prs-status [--repo REPO]` - Get all PRs with CI status
- `pr-checks <pr_number> [--repo REPO]` - Get checks for specific PR
- `failed-checks <pr_number> [--repo REPO]` - Get only failed checks
- `ci-logs <pr_number> [--check NAME] [--repo REPO]` - Get failure logs
