# Claude Code

Status line and the `status-notify` plugin (notifications).

## New machine

- `stow claude` links everything into `~/.claude`
- stow doesn't register the plugin, so do that by hand:

```bash
claude plugin marketplace add ~/.claude/local-mods
claude plugin install status-notify@local-mods
```

- settings.json isn't stowed, so add the status line to it by hand:
  `"statusLine": { "type": "command", "command": "bash ~/.claude/statusline.sh" }`
- restart Claude Code after
- status line needs `jq`
