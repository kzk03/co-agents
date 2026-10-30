You are coding GitHub pull-request reviews with state CHANGES_REQUESTED by the REASON the human reviewer blocked the change. Authors may be AI coding agents or humans. "BODY: nan" means no summary text. Inline comments are shown as [file] text (possibly truncated).

Pick ONE primary category for the reason that most directly caused the change request (the reviewer's emphasis: summary body over inline; explicit blocking words; otherwise the first substantive point). Optionally give ONE secondary category ("also") if a clearly different second reason is present, else "".

Decision procedure (apply in order, stop at the first YES):
0. X — No substantive reason at all (procedural: "requesting changes so the bot understands", "abandoning this review", empty).
1. C — The objection is about properties of the change itself that a competent engineer could raise from the diff, the repository code/config, the request/issue the author was given, and widely shared engineering knowledge. Includes violating the explicit request/spec that was given to the author, widely shared norms (don't delete user data), general design hygiene (single responsibility, duplication).
   C1 correctness/regression/incompleteness/spec non-compliance; C2 maintainability/style/scope creep/unrelated changes/reuse an existing in-repo mechanism; C3 missing tests/docs/changelog/commit format; M only relays CI failure or merge conflict.
2. Is the reviewer exercising a DECISION that would remain even if the author had every piece of information — choosing among acceptable alternatives, a value/product/UX/game-balance judgment, deciding scope or whether to do it at all, a decision still pending among humans, or holding/timing/accepting risk? If yes:
   D-dir: direction/scope/value choice (what to build, which of several valid designs, whether it is needed, decision not yet agreed).
   D-risk: risk acceptance, holding a merge, sequencing/timing (wait for release, review dependent PR first, blast radius too big, not acceptable without evidence).
3. Does the reason invoke a GENERAL project rule, convention, or design principle that applies beyond this PR (could be written once in README/CONTRIBUTING/AGENTS.md), whether or not it is actually written?
   R-gov: governance rules about who decides/approves or contributor obligations (approval procedure, AI disclosure, CLA, DCO, release/backport policy, ownership).
   R-tech: technical conventions/architecture principles (where logic belongs, "features go into plugins", "never edit generated code", supported versions, API design principles of the project).
4. Does the reason rest on a SPECIFIC FACT outside the diff (other PRs/issues, past history/reverts, external system or platform behavior, deployment/customer reality, plans in someone's head)?
   K-pub: the fact is publicly retrievable in principle (linked issue/PR/commit, git history, public docs/specs of external systems).
   K-priv: the fact is held only by humans (private chats/meetings, customer incidents, the maintainer's unpublished plans or intent, observations from their own environment/operations).
5. UNK — cannot be determined.

Boundary rules:
- General rule vs specific fact: if the reviewer states it as a rule applying to future PRs -> R; if it is a one-off fact -> K.
- Rule vs decision: if the reviewer cites/states a standing rule -> R; if the reviewer decides now for this case -> D.
- An "@agent" instruction is coded by the reason behind it.
- A decision made earlier elsewhere and cited (e.g., "decided in PR #123") -> K-pub; a decision still open ("we are still agreeing") -> D-dir.

Also give "doc": could the reason have been written down in the repository's documentation BEFORE this PR existed, as a general statement?
- could: yes, as a general statement (rules, conventions, stable facts such as supported versions or platform behavior)
- no: it only arises on the spot (depends on this PR's specifics, in-flight work, current timing, a one-off judgment)
- "-": for C, X, UNK

Output ONLY JSON lines, one per item, no prose, no code fences:
{"sid":"G001","cat":"R-tech","also":"","doc":"could"}
