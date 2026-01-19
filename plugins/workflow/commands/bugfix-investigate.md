---
description: Investigate a bug from Linear ticket with Sentry analysis
---

# Bug Investigation

Input: $ARGUMENTS (Linear ticket ID)

## Step 1: Fetch Context

Get ticket details:
```bash
python plugins/workflow/tools/linear.py get-ticket <ticket_id>
```

Extract Sentry URL from description, then use Sentry MCP tools:
- `mcp__sentry__get_issue_details` for issue info
- `mcp__sentry__analyze_issue_with_seer` for AI root cause analysis

## Step 2: Create Fix Plan
Use the **debugger** agent to analyze and create a fix plan:
- Files to modify
- Specific changes needed
- Edge cases to consider

## Step 3: Document in Linear
Add investigation findings as a comment:
```bash
python plugins/workflow/tools/linear.py add-comment <ticket_id> --body "## Root Cause Analysis

<findings>

## Affected Code
- <file1>:<line>
- <file2>:<line>

## Proposed Fix
<fix plan>"
```

**DO NOT implement yet** - just investigate and plan.

## Tool Reference

### Linear (`plugins/workflow/tools/linear.py`)
- `get-ticket <ticket_id>` - Get ticket details with description
- `add-comment <ticket_id> --body "text"` - Add comment

### Git (`plugins/workflow/tools/git.py`)
- `github-repo` - Get GitHub repo for context
