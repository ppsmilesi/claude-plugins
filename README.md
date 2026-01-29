# claude-workflow-plugin

## Reinstalling the plugin

After making changes to the plugin source, reinstall to update the cached version:

```bash
# 1. Remove the installed cache
rm -rf ~/.claude/plugins/cache/*/workflow/

# 2. Reinstall from the local marketplace
claude plugins install workflow
```

The plugin cache lives at `~/.claude/plugins/cache/<marketplace>/workflow/<version>/`. Skills, agents, and tools are copied there at install time, so any source changes require a reinstall.
