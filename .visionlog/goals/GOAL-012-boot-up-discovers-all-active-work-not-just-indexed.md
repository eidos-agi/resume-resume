---
id: "GOAL-012"
type: "goal"
title: "boot_up discovers all active work, not just indexed sessions"
status: "active"
date: "2026-03-25"
depends_on: []
unlocks: []
---

boot_up should scan known project directories for dirty git state (uncommitted files, recent commits) in addition to querying the session index. This closes a core reliability gap where interrupted work is invisible to boot_up if the session wasn't indexed. Dirty files and recent commits are the strongest signals of where work was happening — stronger than session metadata.
