---
description: Refine a vague idea into a well-structured prompt for use with other workflow commands
---

# Prompt Refinement

Input: $ARGUMENTS (rough idea, feature request, or bug description)

## Purpose
Transform vague ideas into structured, actionable prompts that work well with:
- `/workflow:feature-plan` - For planning new features
- `/workflow:feature-implement` - For implementing features
- `/workflow:bugfix-investigate` - For bug investigation
- Linear ticket creation

## Workflow

### Step 1: Analyze Input
Use the **refiner** agent to analyze the user's rough idea:
- Identify the type (feature, bug, refactoring, improvement)
- Detect missing information
- Note ambiguities

### Step 2: Gather Context
If in a repository, quickly check:
```bash
python plugins/workflow/tools/git.py repo-name
```
And scan for relevant patterns in the codebase.

### Step 3: Ask Clarifying Questions
The **refiner** agent will ask 3-5 targeted questions:
- Focus on the most impactful gaps
- Conversational tone, not a checklist
- Offer suggestions where appropriate

### Step 4: Generate Refined Prompt
Structure the output as:

```markdown
## <Type>: <Title>

### Summary
<Clear 2-3 sentence description>

### Requirements
- <Specific, actionable requirement>
- ...

### Acceptance Criteria
- [ ] <Testable criterion>
- ...

### Technical Considerations
- <Relevant constraints or notes>

### Out of Scope
- <Explicitly excluded items>

### Suggested Next Step
`/workflow:feature-plan` or `/workflow:feature-implement`
```

### Step 5: Offer Next Actions
Present options:
1. **Use now**: Pipe directly to another workflow command
2. **Copy**: User copies the refined prompt for later
3. **Create ticket**: Create a Linear ticket with the refined content
4. **Iterate**: Refine further if needed

## Examples

### Input
```
add dark mode
```

### Clarifying Questions
"A few questions to make this actionable:
1. Where should the toggle live - settings page, header, or follow system preference?
2. Should the preference persist across sessions?
3. Are there existing design tokens/CSS variables, or do we need to create them?"

### Refined Output
```markdown
## Feature: Dark Mode Support

### Summary
Add a dark mode theme option that users can toggle from the settings page.
The preference persists in localStorage and applies to all application components.

### Requirements
- Add theme toggle switch in Settings > Appearance
- Implement dark color palette using CSS variables
- Persist user preference in localStorage
- Respect system preference as default (prefers-color-scheme)

### Acceptance Criteria
- [ ] Toggle switches between light and dark themes
- [ ] Theme preference persists across browser sessions
- [ ] All components render correctly in both themes
- [ ] No flash of incorrect theme on page load
- [ ] System preference is respected when no user preference set

### Technical Considerations
- Use CSS custom properties for theme tokens
- Consider existing component library theming support
- Test contrast ratios for accessibility (WCAG AA)

### Out of Scope
- Auto-switching based on time of day
- Per-component theme overrides

### Suggested Next Step
`/workflow:feature-plan` to create architecture and Linear tickets
```

## Tips
- The more context you provide initially, the fewer questions needed
- You can run `/workflow:refine` multiple times to iterate
- Works for features, bugs, refactoring, documentation, anything
