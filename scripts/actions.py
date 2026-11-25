"""Bash コマンドを行為の種類に分類する(決定的な規則のみ)。

1. heredoc と引用符の中身を除く(コミットメッセージ等の単語に当たらないように)
2. && || ; | 改行 で区切る
3. 各区切りの先頭のプログラムとサブコマンドで分類する(VAR=x, sudo, rtk などの前置きは飛ばす)
4. 区切りの中で最も重い行為(PRIORITY の先頭寄り)を採る
"""
import os
import re

PRIORITY = [
    "publish", "deploy", "git_push", "gh_pr_merge", "gh_pr_create", "gh_write",
    "git_commit", "git_history", "delete", "git_add", "pkg_install", "db", "network",
    "process_kill", "file_ops", "test_build", "run", "bash_other", "git_read", "wait", "read_only",
]
RANK = {a: i for i, a in enumerate(PRIORITY)}

HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?.*?\n\s*\1\b", re.S)
HEREDOC_REST = re.compile(r"<<.*", re.S)
QUOTED = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'[^']*'", re.S)
SPLIT = re.compile(r"&&|\|\||[;|\n]|\$\(|`|\)")
WRAPPERS = {"sudo", "rtk", "env", "time", "nohup", "command", "exec", "xargs", "timeout", "proxy", "caffeinate"}

READ_ONLY = {"cd", "cat", "ls", "grep", "rg", "find", "head", "tail", "echo", "pwd", "wc", "which", "tree",
             "sed", "awk", "sort", "uniq", "jq", "stat", "file", "less", "diff", "printf", "true", "test",
             "[", "type", "realpath", "dirname", "basename", "du", "df", "date", "whoami", "env", "fd", "bat",
             "cut", "tr", "xxd", "md5", "shasum", "sha256sum", "strings", "otool", "nl", "column", "zcat", "gzcat", "export", "source", "."}
FILE_OPS = {"cp", "mv", "mkdir", "touch", "chmod", "chown", "ln", "tar", "unzip", "zip", "tee", "install"}
NETWORK = {"curl", "wget", "ssh", "scp", "rsync", "nc", "http", "sftp"}
DB = {"psql", "mysql", "sqlite3", "mongosh", "mongo", "redis-cli", "prisma", "drizzle-kit", "alembic", "clickhouse", "clickhouse-client", "duckdb"}
KILL = {"kill", "pkill", "killall", "lsof"}
TEST_BUILD = {"pytest", "jest", "vitest", "tsc", "eslint", "ruff", "mypy", "biome", "make", "xcodebuild",
              "gradle", "gradlew", "./gradlew", "mvn", "prettier", "golangci-lint", "swift", "playwright",
              "black", "shellcheck", "cmake", "ninja", "bazel", "pyright", "rspec", "phpunit", "tox", "nox", "zig"}
RUN = {"python", "python3", "node", "deno", "docker", "npx", "bunx", "uvx", "mise", "just", "bash", "sh", "zsh",
       "ruby", "go", "cargo", "open", "osascript", "tmux", "screen", "claude", "codex", "entire", "watch", "pnpx"}
TB_WORD = re.compile(r"^(test|tests|lint|build|check|typecheck|type-check|check-types|fmt|format|verify|ci|e2e|tsc|vet|clippy)([:\-].*)?$")
WRITE_VERB = {"create", "edit", "close", "comment", "review", "delete", "rerun", "ready", "reopen", "merge", "set", "cancel", "transfer", "lock", "archive", "rename", "upload"}


def skeleton(cmd: str) -> str:
    s = HEREDOC.sub(" ", cmd)
    s = HEREDOC_REST.sub(" ", s)
    return QUOTED.sub("Q", s)


def classify_segment(tokens):
    while tokens and (re.match(r"^\w+=", tokens[0]) or tokens[0] in WRAPPERS or tokens[0].startswith("-")):
        tokens = tokens[1:]
    if not tokens:
        return None
    prog = os.path.basename(tokens[0])
    args = tokens[1:]
    words = [a for a in args if not a.startswith("-")]
    w0 = words[0] if words else ""
    w1 = words[1] if len(words) > 1 else ""
    if any(w.startswith("deploy") for w in words) and prog not in ("git", "cat", "ls", "grep", "rg", "find"):
        return "deploy"
    if prog == "git":
        # -C path / -c key=val の値を飛ばす
        rest, i = [], 0
        while i < len(args):
            if args[i] in ("-C", "-c", "--git-dir", "--work-tree"):
                i += 2; continue
            if not args[i].startswith("-"):
                rest.append(args[i])
            i += 1
        sub = rest[0] if rest else ""
        if sub == "push": return "git_push"
        if sub == "commit": return "git_commit"
        if sub == "add": return "git_add"
        if sub in ("reset", "rebase", "revert", "cherry-pick", "stash", "merge", "checkout", "switch",
                   "restore", "clean", "tag", "worktree", "rm", "mv", "pull", "am", "apply", "filter-branch"):
            return "git_history"
        if sub == "branch" and any(a in ("-d", "-D", "-m", "-M", "--delete") for a in args): return "git_history"
        return "git_read"
    if prog == "gh":
        if w0 == "pr" and w1 == "merge": return "gh_pr_merge"
        if w0 == "pr" and w1 == "create": return "gh_pr_create"
        if w0 == "release" and w1 == "create": return "publish"
        if w1 in WRITE_VERB: return "gh_write"
        if w0 == "api" and any(a.upper() in ("POST", "PATCH", "PUT", "DELETE") or a.startswith("-XP") or a.startswith("-XD") for a in args):
            return "gh_write"
        return "git_read"
    if prog in ("npm", "pnpm", "yarn", "bun"):
        if w0 == "publish": return "publish"
        if w0 in ("install", "add", "i", "remove", "uninstall", "ci", "rm", "update", "upgrade"): return "pkg_install"
        if w0 == "run" or w0 == "--filter":
            tgt = next((w for w in words[1:] if not w.startswith("@") or True), "")
            return "test_build" if TB_WORD.match(tgt or "") else "run"
        if TB_WORD.match(w0): return "test_build"
        return "run"
    if prog in ("pip", "pip3", "brew", "apt", "apt-get", "gem", "poetry", "conda"):
        if w0 in ("install", "uninstall", "add", "remove", "upgrade", "update"): return "pkg_install"
        if prog == "gem" and w0 == "push": return "publish"
        return "read_only" if w0 in ("list", "show", "freeze", "info", "search") else "pkg_install"
    if prog == "uv":
        if w0 in ("add", "remove", "pip", "sync", "lock"): return "pkg_install"
        if w0 == "publish": return "publish"
        return "run"
    if prog == "cargo":
        if w0 == "publish": return "publish"
        if w0 in ("add", "install", "remove", "update"): return "pkg_install"
        if w0 in ("test", "check", "build", "clippy", "fmt", "nextest", "bench", "llvm-cov"): return "test_build"
        return "run"
    if prog == "go":
        if w0 in ("test", "build", "vet", "fmt"): return "test_build"
        if w0 in ("get", "install"): return "pkg_install"
        if w0 == "mod": return "pkg_install" if w1 in ("tidy", "download") else "read_only"
        return "run"
    if prog == "docker":
        if w0 == "push": return "publish"
        if w0 in ("rm", "rmi") or "prune" in words: return "delete"
        if w0 in ("ps", "images", "logs", "inspect"): return "read_only"
        return "run"
    if prog in ("kubectl", "helm"):
        return "deploy" if w0 in ("apply", "delete", "rollout", "install", "upgrade", "uninstall", "scale", "patch") else "read_only"
    if prog == "terraform":
        return "deploy" if w0 in ("apply", "destroy", "import") else "test_build"
    if prog in ("vercel", "wrangler", "fly", "flyctl", "netlify", "firebase", "supabase", "railway", "heroku", "aws", "gcloud", "az", "pulumi"):
        return "deploy" if any(w in ("deploy", "publish", "up", "push", "apply", "delete", "destroy", "launch") for w in words) else "network"
    if prog in ("mise", "just", "task", "make") and w0:
        tgt = w1 if w0 == "run" else w0
        if TB_WORD.match(tgt): return "test_build"
        return "test_build" if prog == "make" else "run"
    if prog in ("rm", "rmdir", "unlink", "trash", "shred"): return "delete"
    if prog in NETWORK: return "network"
    if prog in DB: return "db"
    if prog in KILL: return "process_kill"
    if prog in FILE_OPS: return "file_ops"
    if prog in TEST_BUILD: return "test_build"
    if prog in RUN or prog.startswith("python") or prog.endswith(".sh") or prog.endswith(".py"): return "run"
    if prog == "sleep": return "wait"
    if prog in READ_ONLY: return "read_only"
    return "bash_other"


def classify_command(cmd: str) -> str:
    if not isinstance(cmd, str) or not cmd.strip():
        return "bash_other"
    best = None
    for seg in SPLIT.split(skeleton(cmd)):
        a = classify_segment(seg.split())
        if a and (best is None or RANK[a] < RANK[best]):
            best = a
    return best or "bash_other"


if __name__ == "__main__":
    tests = {
        "git add a.ts && git commit -m \"$(cat <<'EOF'\nfix: push the thing to vercel\nEOF\n)\"": "git_commit",
        "git push -u origin docs/clarify-vercel-env-selection 2>&1 | tail -10": "git_push",
        "git add .github/workflows/deploy-direct.sh": "git_add",
        "mise run deploy:local 2>&1 | tail -30": "deploy",
        "docker system prune -af 2>&1 | tail -2": "delete",
        "rm -rf /tmp/x; go test ./... | head": "delete",
        "cd /repo && ls -la": "read_only",
        "rtk git -C /x -c commit.gpgsign=false commit -m Q": "git_commit",
        "gh pr create --title \"x\" --body \"$(cat <<'EOF'\nmerge later\nEOF\n)\"": "gh_pr_create",
        "GIT_CONFIG_COUNT=1 mise run test 2>&1 | grep x": "test_build",
        "supabase functions deploy leaderboard-submit": "deploy",
        "npm install 2>&1 | tail -5": "pkg_install",
        "bun run lint": "test_build",
        "gh pr view 12 --json title": "git_read",
        "sleep 30 && gh run view 1": "git_read",
    }
    bad = [(c, e, classify_command(c)) for c, e in tests.items() if classify_command(c) != e]
    for c, e, g in bad:
        print(f"FAIL expected={e} got={g} :: {c!r}")
    print(f"{len(tests) - len(bad)}/{len(tests)} ok")
