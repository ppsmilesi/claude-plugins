---
name: feature-plan
description: Plan a new feature with architecture design and Linear ticket creation
disable-model-invocation: true
argument-hint: "[feature description]"
---

# Feature Planning

Transform requirements into a complete Linear project with well-documented tickets ready for implementation.

Input: $ARGUMENTS (feature description - ideally from `/workflow:refine`)

---

## Step 1: Capture Requirements

If input is provided, use it directly. Otherwise, ask for:
- Feature name/title
- Feature description (what should it do?)
- Linear team (default: staff)

**TIP**: For best results, run `/workflow:refine` first to structure the requirements.

---

## Step 2: Architecture Analysis

Use the **architect** agent to:
1. Explore the codebase to understand existing patterns
2. Design the solution architecture
3. Break down into implementable tasks

The architect will output TWO sections:
- **PROJECT_DESCRIPTION**: Full context for the Linear project
- **TASKS**: JSON array of task definitions

---

## Step 3: Create Linear Project

Create the project with the full PROJECT_DESCRIPTION:

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py create-project \
  --team TEAM \
  --name "Feature: <feature name>" \
  --description "PROJECT_DESCRIPTION content here"
```

The project description MUST contain:
- Original requirements (verbatim)
- Architecture overview
- Tech stack context
- Key decisions with rationale
- Reference files showing patterns
- Out of scope items

---

## Step 4: Create Linear Tickets

For each task from the architect's TASKS output:

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py create-ticket \
  --team TEAM \
  --title "<task title>" \
  --description "<full task description>" \
  --project <project_id> \
  --state "Todo"
```

Each ticket description MUST contain:
- **Summary**: What this task accomplishes
- **Acceptance Criteria**: Checkboxes for testable criteria
- **Files to Create**: Exact paths with purpose
- **Files to Modify**: Exact paths with what changes
- **Patterns to Follow**: References to existing code
- **Dependencies**: Which other tickets must be done first
- **Notes**: Implementation hints

---

## Step 4b: Set Blocking Relations

For each ticket that has dependencies, set the "blocked by" relation in Linear so that dependency tiers are enforced:

1. Build a mapping of **task title → ticket ID** from the tickets created in Step 4
2. For each task in the architect's TASKS output that has non-empty `dependencies`:
   - Look up each dependency title in the mapping to get the blocker ticket ID
   - Call `block-ticket` to create the relation:

```bash
python ~/.claude/plugins/cache/*/workflow/*/tools/linear.py block-ticket <ticket_id> --blocked-by <blocker_ticket_id>
```

This ensures that:
- Tier 0 tickets have no blockers
- Tier N tickets are blocked by their dependencies from tiers < N
- Linear displays the correct dependency graph

---

## Step 5: Summary

Present to the user:

```
## Feature: <name>

### Linear Project
<project_url>

### Tickets Created
1. <ticket_identifier> - <title> (<url>)
2. <ticket_identifier> - <title> (<url>)
...

### Architecture Summary
<brief overview>

### Next Step
Run `/workflow:feature-implement <ticket_id>` for each ticket to implement
```

---

## Example Output

```
## Feature: Dark Mode Support

### Linear Project
https://linear.app/team/project/dark-mode-abc123

### Tickets Created
1. STAFF-101 - Create design tokens for theming
2. STAFF-102 - Implement ThemeProvider context
3. STAFF-103 - Add theme toggle to Settings page
4. STAFF-104 - Update components to use theme tokens
5. STAFF-105 - Add dark mode tests

### Architecture Summary
CSS custom properties based theming with React Context.
Theme preference stored in localStorage with system preference fallback.

### Next Step
Run `/workflow:feature-implement STAFF-101` to start implementing tickets
```

---

## Tool Reference

### Linear (`~/.claude/plugins/cache/*/workflow/*/tools/linear.py`)
- `create-project --team TEAM --name NAME --description DESC`
- `create-ticket --team TEAM --title TITLE --description DESC --project ID --state STATE`
- `block-ticket <ticket_id> --blocked-by <blocker_ticket_id>` — Set blocking relation

### Git (`~/.claude/plugins/cache/*/workflow/*/tools/git.py`)
- `repo-name` - Get repository name
- `github-repo` - Get GitHub repo (owner/repo)

---

## Quality Checklist

Before finishing, verify:
- [ ] Project description contains original requirements
- [ ] Project description has architecture overview
- [ ] Project description lists reference files
- [ ] Each ticket has acceptance criteria
- [ ] Each ticket has specific file paths
- [ ] Each ticket references patterns to follow
- [ ] Tickets are ordered by dependency
- [ ] Blocking relations set in Linear for all dependencies
- [ ] No documentation files created in codebase
