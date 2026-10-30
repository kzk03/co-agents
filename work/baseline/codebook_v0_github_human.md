You are coding GitHub pull-request reviews with state CHANGES_REQUESTED, written by human reviewers on pull requests authored by human developers, by the REASON the reviewer blocked the change. "BODY: nan" means the review had no summary text.
Each item = the review summary (BODY) plus the reviewer's inline comments in that review ([file] ...).
Pick ONE primary category = the reason that most directly caused the change request. Instructions addressed to the author are coded by the reason behind the instruction.

C-group (reason derivable from the code and in-repo artifacts):
- C1 Correctness/incompleteness: bug, logic error, missed places that need the same fix, wrong test, failing tests that look legitimate.
- C2 Maintainability/style: naming, duplication, nits, unrelated change mixed in, should reuse an existing in-repo mechanism.
- C3 Missing accompanying artifacts: missing/incorrect tests, release notes, docs, commit message format/content.
- M Mechanical: merely relaying CI failure or merge conflict.
H-group (reason requires human context or judgment):
- H1 Human context: depends on knowledge of other in-flight patches/work, agreements in meetings/ML, duplicate or superseding patches, historical background.
- H2 Policy/design judgment: where/how it should be solved, whether it should be done at all, responsibility split between components/projects, scope.
- H3 Implicit assumptions: deployment topology, backend/hardware behavior, external standards, operational reality outside the repository.
- H4 Process/governance/responsibility: spec freeze, backport policy, branch lifecycle, approval procedure, whether someone owns/champions the work, release sequencing.
- H5 Security/permission/risk: who is allowed to do what, security impact, admin-only decisions.
Other:
- BOT: automated third-party CI report posted by a bot-like account.
- UNK: reason cannot be determined from the text.

Also label "inferable": could an LLM agent given ONLY the diff and the repository contents (code + in-repo docs) raise the same objection?
- yes: diff + repo is enough
- partial: some in-repo hints, but domain knowledge or other repositories' knowledge is needed
- no: needs information outside the repository (meetings, mailing lists, other in-flight patches, operational reality, policy)
- "-" for BOT/UNK

Output ONLY JSON lines, one per item, no prose, no code fences:
{"sid":"S001","cat":"H1","inferable":"no"}
