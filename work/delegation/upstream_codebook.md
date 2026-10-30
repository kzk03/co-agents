# Upstream judgment codebook (delegation, v0)

Each ITEM is one GitHub pull request. You get:
- REQUEST: the text written BEFORE the PR (a linked issue with its comments made before the PR, or the original prompt given to a coding agent). `src=pr_body_proxy` means no issue/prompt was found and the PR description itself (often written by the agent, possibly edited after review) is shown as a weak proxy. `(none)` means nothing is available.
- REVIEW (CR): one reviewer's "changes requested" review (summary BODY plus inline comments `[path] text`).

Task: identify the reviewer's MAIN point (the one that most drives the change request; if several are equally important, take the most consequential / design-level one) and decide where that point first appears.

Labels (`up`):
- `U1` — The main point (requirement, constraint, context or policy) is already stated in the REQUEST, and the review restates, refines or extends it in the same direction (the judgment existed upstream; the review re-emphasizes or concretizes it).
- `U2` — The REQUEST explicitly asked for X (or forbade Y), the PR did not follow it, and the review points out that non-compliance (e.g. "I asked for the root cause", "must work on Windows" when the request said so).
- `U3` — The main point is NOT in the REQUEST (neither explicitly nor clearly implied): it first appears at review. Includes reviewer changing direction, new constraints, conventions, test/CI failures, code-level fixes.
- `U4` — Cannot judge: REQUEST is `(none)`; or the linked issue is clearly unrelated to the PR's task (e.g. a template placeholder issue like #123); or the review has no substantive point (empty, "Revert", "Address comments", "(see below)", "Abandoning review").

Also give `dec`: does the REQUEST (issue/prompt only; answer `NA` for pr_body_proxy, (none) or unrelated issue) contain at least one explicit design decision, constraint, policy or rationale beyond the bare task statement (e.g. "use X", "don't do Y", "keep backward compatibility", "only for modern .NET", reasons for choosing an approach)? `Y` or `N`.

Output: one JSON object per line, nothing else, in item order:
{"sid": "G001", "up": "U3", "dec": "Y", "req_quote": "<=120 chars from REQUEST supporting U1/U2, else empty", "rev_quote": "<=120 chars of the main review point"}
