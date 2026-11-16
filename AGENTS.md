# AGENTS.md

Rules for AI coding agents working in this repo. Project facts, layout and commands are in
[CLAUDE.md](CLAUDE.md); this file holds the working rules for agents and subagents.

## Subagents

- **At most 2 subagents at any one time.** Queue further work and start the next agent only when
  one finishes. Review agents count toward the limit. Do small checks and reviews inline instead.
- **Subagents never spawn subagents.** A subagent does its task itself; if it needs more help it
  reports back to the agent that started it.
