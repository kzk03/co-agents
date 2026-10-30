# HUMANS.md — What maintainers must supply

The repo is runnable without external services (stubbed LLM & in-memory KG). To enable full features:

1. **OpenAI (optional)**
   - `OPENAI_API_KEY` with access to `gpt-5-codex` and `text-embedding-3-large`
   - Optional: set `OPENAI_BASE_URL` if using a proxy or Azure OpenAI compatible endpoint.
 - Set `EMBEDDINGS_PROVIDER=openai` (and optionally `OPENAI_EMBED_MODEL`) to
    enable remote embeddings; default remains deterministic offline vectors.

2. **Neo4j (optional)**
   - Set `GRAPH_BACKEND=neo4j` plus `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` to enable the graph store.

3. **Web search tool**
   - Tweak `WEB_SEARCH_CACHE_TTL`, `WEB_SEARCH_CACHE_MAXSIZE`, `WEB_SEARCH_RATE_LIMIT`,
     and `WEB_SEARCH_RATE_PERIOD` if you need different cache/throughput settings.

4. **Conversation persistence**
   - `SESSIONS_DB_PATH` controls where the SQLite conversation store lives (defaults to
     `./data/sessions.db`).
   - `SESSION_TTL_SECONDS` prunes conversations that have been inactive for the given
     number of seconds (default: 604800 seconds / 7 days).
   - Set `SESSIONS_DB_URL` to a `postgres://` DSN to persist sessions in Postgres.

5. **Policy & safety**
   - `POLICY_MAX_TOKENS` limits combined request tokens (approximate, default 1200).
   - `POLICY_BLOCK_PATTERN` (regex) blocks risky content; defaults to a basic keyword list.
   - `TOOL_ALLOWLIST` restricts which orchestrator tools can run (comma-separated names).
   - `TOOL_MAX_CALLS_PER_SESSION` caps tool invocations per session (default 5).

3. **Production infra**
   - Container registry, environment secrets, HTTPS (e.g., via your platform).
   - Observability (logs, traces, metrics).

4. **Policies**
   - Security review for any tool that touches the network or filesystem outside the workspace.
   - Data retention & PII handling rules.

5. **Sign-offs**
   - Changes to `.github/workflows/`, licensing, or public API require explicit approval.
