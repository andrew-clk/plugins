#!/usr/bin/env python3
"""PreToolUse guard for irreversible shell commands, shared by Claude Code and Codex.

Claude Code gets "ask", so Andrew confirms in the UI. Codex rejects "ask", so it gets
"deny" and the reason hands the exact command back for Andrew to run himself.
This is a speed bump for a cooperative agent, not a sandbox: it parses common shell
forms, and anything it cannot parse is allowed, because a crashing guard must not
block every Bash call. tests/test_guard.py pins each rule.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from urllib.parse import urlsplit

PROTECTED_BRANCHES = {"main", "master"}
MONEY_DOMAINS = ("bukku.my", "lalamove.com")
NON_LIVE_HOST = re.compile(r"sandbox|staging|^developers\.", re.I)
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

NEWLINE = "\x01"
SEPARATORS = {";", "&&", "||", "&", NEWLINE, "(", ")", ";;"}
PIPES = {"|", "|&"}
SHELL_KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "time"}
WRAPPERS = {"sudo", "command", "exec", "nohup", "env", "nice", "doas"}
WRAPPER_VALUE_OPTS = {"-u", "-g", "-C", "-h", "-p"}
PACKAGE_RUNNERS = {"npx", "bunx", "pnpx"}
RUNNER_SUBCOMMANDS = {"dlx", "exec", "x"}
SHELLS = {"bash", "sh", "zsh", "dash"}

SQL_CLIENTS = {"psql", "mysql", "mariadb", "pgcli"}
SQL_DESTRUCTIVE = [
    re.compile(r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b", re.I),
    re.compile(r"\bTRUNCATE\b", re.I),
    re.compile(r"\bDELETE\s+FROM\s+[\w.\"`]+(?![^;]*\bWHERE\b)", re.I),
    re.compile(r"\bUPDATE\s+[\w.\"`]+\s+SET\b(?![^;]*\bWHERE\b)", re.I),
]

VERCEL_VALUE_OPTS = {"--scope", "-S", "--token", "-t", "--cwd", "--local-config", "-A",
                     "--global-config", "-Q", "--team", "-T", "--target"}
VERCEL_LOCAL = {"build", "pull", "dev", "env", "logs", "inspect", "ls", "list", "whoami",
                "link", "login", "logout", "domains", "certs", "dns", "help", "init", "git"}
VERCEL_LIVE = {"promote", "rollback", "remove", "rm", "redeploy"}
RAILWAY_VALUE_OPTS = {"--service", "-s", "--environment", "-e", "--project", "-p",
                      "--message", "-m"}
DEPLOY_HELP_VALUE_OPTS = VERCEL_VALUE_OPTS | {
    "--env", "-e", "--build-env", "-b", "--meta", "-m", "--archive", "--regions",
    "--name", "-n", "--listen", "-l",
}
REDIRECTIONS = {">", ">>", "<", "<<", "<<<", "<>", "&>", "&>>", ">&", ">|", "<&"}
CURL_SHORT_VALUE = set("AbcCdDeEFHKmoPQrTuUwxXyYz")
CURL_LONG_VALUE = {"--request", "--data", "--data-raw", "--data-binary", "--data-urlencode",
                   "--data-ascii", "--json", "--form", "--form-string", "--upload-file", "--header",
                   "--output", "--user", "--user-agent", "--referer", "--cookie", "--cookie-jar",
                   "--max-time", "--proxy", "--url", "--write-out", "--config", "--range"}


def tokenize(command: str) -> list[str]:
    # The marker sits after each newline so a comment, which shlex drops through the
    # end of its line, cannot swallow the command on the next line.
    marked = command.replace("\n", f"\n {NEWLINE} ")
    lexer = shlex.shlex(marked, posix=True, punctuation_chars=True)
    lexer.whitespace = " \t\r\n"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = marked.split()
    return [t if t == NEWLINE else t.replace(f"\n {NEWLINE} ", "\n") for t in tokens]


def pipelines(command: str) -> list[list[list[str]]]:
    """Split a command into pipelines, each a list of argv segments joined by pipes."""
    result: list[list[list[str]]] = [[[]]]
    for token in tokenize(command):
        if token in SEPARATORS:
            result.append([[]])
        elif token in PIPES:
            result[-1].append([])
        else:
            result[-1][-1].append(token)
    cleaned = []
    for pipeline in result:
        segs = [seg for seg in map(strip_prefix, pipeline) if seg]
        if segs:
            cleaned.append(segs)
    return cleaned


def strip_prefix(argv: list[str]) -> list[str]:
    i = 0
    while i < len(argv):
        token = argv[i]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token) or token in SHELL_KEYWORDS:
            i += 1
        elif token in WRAPPERS:
            i += 1
            while i < len(argv) and argv[i].startswith("-"):
                i += 2 if argv[i] in WRAPPER_VALUE_OPTS else 1
        elif token in PACKAGE_RUNNERS or (token in {"pnpm", "yarn", "npm", "bun"} and argv[i + 1 : i + 2] and argv[i + 1] in RUNNER_SUBCOMMANDS):
            i += 1 if token in PACKAGE_RUNNERS else 2
            while i < len(argv) and argv[i].startswith("-"):
                i += 1
        else:
            break
    argv = argv[i:]
    if argv:
        argv[0] = os.path.basename(argv[0])
    return argv


def git(cwd: str, *args: str) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5, check=False)
        return out.stdout.split()
    except (OSError, subprocess.SubprocessError):
        return []


def check_git_push(argv: list[str], cwd: str, branch: str | None = None) -> str | None:
    if not argv or argv[0] != "git":
        return None
    i, config_push, push_default = 1, [], None
    while i < len(argv) and argv[i].startswith("-"):
        if argv[i] in {"-C", "-c", "--git-dir", "--work-tree"} and i + 1 < len(argv):
            if argv[i] == "-C":
                cwd = os.path.join(cwd, argv[i + 1])
            key, _, value = argv[i + 1].partition("=")
            if argv[i] == "-c" and key.startswith("remote.") and key.endswith(".push"):
                config_push.append(value)
            if argv[i] == "-c" and key == "push.default":
                push_default = value
            i += 2
        else:
            i += 1
    if i >= len(argv) or argv[i] != "push":
        return None

    args = argv[i + 1 :]
    flags, positional, j = [], [], 0
    while j < len(args):
        if args[j] in {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}:
            j += 2
            continue
        (flags if args[j].startswith("-") else positional).append(args[j])
        j += 1
    short = "".join(f[1:] for f in flags if re.fullmatch(r"-[A-Za-z]+", f))
    if "n" in short or "--dry-run" in flags:
        return None
    if "--mirror" in flags:
        return "git push --mirror rewrites every branch on the remote, main included."
    force_all = "f" in short or any(f.startswith("--force") for f in flags)
    delete_all = "d" in short or "--delete" in flags

    remote = positional[0] if positional else "origin"
    refspecs = positional[1:]
    if not refspecs:
        refspecs = config_push or git(cwd, "config", "--get-all", f"remote.{remote}.push")
    if not refspecs and "--tags" not in flags:
        push_default = push_default or next(iter(git(cwd, "config", "--get", "push.default")), "")
        if force_all and push_default == "matching":
            return "git push --force with push.default=matching can rewrite main and master."
        refspecs = [branch] if branch else git(cwd, "symbolic-ref", "--short", "-q", "HEAD")
    if "--all" in flags or "--branches" in flags:
        refspecs = [*refspecs, "main"]

    head = None
    for spec in refspecs:
        force = force_all or spec.startswith("+")
        spec = spec.lstrip("+")
        if spec == ":":
            if force:
                return "git push +: force-pushes every matching branch, main included."
            continue
        delete = delete_all or spec.startswith(":")
        raw_dst = spec.split(":", 1)[-1]
        if raw_dst.startswith("refs/") and not raw_dst.startswith("refs/heads/"):
            continue
        dst = raw_dst.removeprefix("refs/heads/")
        if dst == "HEAD":
            head = head or branch or (git(cwd, "symbolic-ref", "--short", "-q", "HEAD") or [""])[0]
            dst = head
        protected = dst in PROTECTED_BRANCHES or any(fnmatch.fnmatchcase(b, dst) for b in PROTECTED_BRANCHES)
        name = dst if dst in PROTECTED_BRANCHES else "main"
        if protected and force:
            return f"force-push to {name}. Global rule: never force-push main."
        if protected and delete:
            return f"deletes the remote {name} branch."
    return None


def subcommand(rest: list[str], value_opts: set[str]) -> str:
    j = 0
    while j < len(rest):
        if rest[j] in value_opts:
            j += 2
        elif rest[j].startswith("-"):
            j += 1
        else:
            return rest[j]
    return ""


def requests_help(rest: list[str], value_opts: set[str]) -> bool:
    """Recognize a help flag only where the CLI would receive an option."""
    j = 0
    while j < len(rest):
        token = rest[j]
        if token == "--":
            return False
        if token in value_opts or token in REDIRECTIONS:
            j += 2
            continue
        if token in {"--help", "-h"}:
            return True
        j += 1
    return False


def check_deploy(argv: list[str]) -> str | None:
    if not argv:
        return None
    tool, rest = argv[0], argv[1:]
    if tool == "vercel":
        if requests_help(rest, DEPLOY_HELP_VALUE_OPTS):
            return None
        sub = subcommand(rest, VERCEL_VALUE_OPTS)
        if sub in VERCEL_LOCAL:
            return None
        prod = any(a in {"--prod", "--production", "--target=production"} for a in rest) or any(
            a == "--target" and rest[j + 1 : j + 2] == ["production"] for j, a in enumerate(rest)
        )
        if sub in VERCEL_LIVE or prod:
            return f"vercel {sub or 'deploy'} changes production directly, outside git history."
    if tool == "railway":
        if requests_help(rest, RAILWAY_VALUE_OPTS):
            return None
        sub = subcommand(rest, RAILWAY_VALUE_OPTS)
        if sub in {"up", "redeploy", "down", "delete"}:
            return f"railway {sub} changes a live Railway service."
    return None


def host_of(token: str) -> str:
    if not re.match(r"^(?:https?://)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?::\d+)?(?:[/?#]|$)", token, re.I):
        return ""
    return (urlsplit(token if "://" in token else f"//{token}").hostname or "").lower()


def is_live_money_host(host: str) -> bool:
    live = any(host == d or host.endswith(f".{d}") for d in MONEY_DOMAINS)
    return live and not NON_LIVE_HOST.search(host)


def curl_transfers(rest: list[str]):
    """Yield (method, urls) per curl transfer, decoding options the way curl does."""
    method, get, data, upload, urls = None, False, False, False, []
    j = 0
    while j < len(rest):
        a = rest[j]
        if a in {"--next", "-:"}:
            yield final_method(method, get, data, upload), urls
            method, get, data, upload, urls = None, False, False, False, []
        elif a.startswith("--"):
            name, eq, value = a.partition("=")
            if not eq and name in CURL_LONG_VALUE and j + 1 < len(rest):
                value = rest[j + 1]
                j += 1
            if name in {"--request", "--method"}:
                method = value.upper()
            elif name == "--get":
                get = True
            elif name == "--upload-file":
                upload = True
            elif name.startswith(("--data", "--json", "--form")):
                data = True
            elif name == "--url":
                urls.append(value)
        elif a.startswith("-") and len(a) > 1:
            for k, ch in enumerate(a[1:], start=1):
                if ch == "G":
                    get = True
                elif ch in CURL_SHORT_VALUE:
                    value = a[k + 1 :]
                    if not value and j + 1 < len(rest):
                        value = rest[j + 1]
                        j += 1
                    if ch == "X":
                        method = value.upper()
                    elif ch in "dF":
                        data = True
                    elif ch == "T":
                        upload = True
                    break
        else:
            urls.append(a)
        j += 1
    yield final_method(method, get, data, upload), urls


def final_method(method, get, data, upload) -> str:
    if method:
        return method
    if get:
        return "GET"
    if upload:
        return "PUT"
    return "POST" if data else "GET"


def http_writes(argv: list[str]):
    tool, rest = argv[0], argv[1:]
    if tool == "curl":
        yield from curl_transfers(rest)
    elif tool == "wget":
        write = any(a.startswith(("--post-data", "--post-file", "--body-data", "--body-file")) for a in rest)
        method = next((a.split("=", 1)[1].upper() for a in rest if a.startswith("--method=")), None)
        method = method or next((rest[j + 1].upper() for j, a in enumerate(rest[:-1]) if a == "--method"), None)
        yield (method or ("POST" if write else "GET")), rest
    elif tool in {"http", "https", "xh"}:
        first = next((a for a in rest if not a.startswith("-")), "")
        if first.upper() in WRITE_METHODS | {"GET", "HEAD", "OPTIONS"}:
            yield first.upper(), rest
        else:
            yield ("POST" if any("=" in a and not a.startswith("-") for a in rest[1:]) else "GET"), rest


def check_money_api(argv: list[str]) -> str | None:
    if not argv or argv[0] not in {"curl", "wget", "http", "https", "xh"}:
        return None
    for method, tokens in http_writes(argv):
        live = [t for t in tokens if is_live_money_host(host_of(t))]
        if live and method in WRITE_METHODS:
            return f"{method} to a live money API ({live[0]}). Test writes as draft-then-void, and only with Andrew watching."
    return None


def clean_sql(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"--[^\n]*", " ", text)
    text = re.sub(r"'(?:[^']|'')*'", "''", text)
    previous = None
    while previous != text:
        previous, text = text, re.sub(r"\([^()]*\)", " ", text)
    return text


def destructive_sql(text: str) -> str | None:
    for pattern in SQL_DESTRUCTIVE:
        match = pattern.search(text)
        if match:
            return f"destructive SQL ({' '.join(match.group(0).split()[:3])}) sent to a database client."
    return None


def heredoc_bodies(command: str):
    """Yield the raw body of each heredoc fed to a database client."""
    lines = command.split("\n")
    for i, line in enumerate(lines):
        match = re.search(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1", line)
        if match and re.search(r"\b(?:psql|mysql|mariadb|pgcli)\b|\brailway\s+connect\b", line):
            body = []
            for later in lines[i + 1 :]:
                if later.strip() == match.group(2):
                    break
                body.append(later)
            yield "\n".join(body)


def check_sql(command: str, lines: list[list[list[str]]]) -> str | None:
    for pipeline in lines:
        for seg in pipeline:
            if seg[0] == "dropdb":
                return "dropdb deletes a database."
            if seg[0] == "prisma" and (seg[1:3] == ["migrate", "reset"] or "--force-reset" in seg or "--accept-data-loss" in seg):
                return "prisma command that wipes or drops data."
            if seg[0] == "drizzle-kit" and "push" in seg and "--force" in seg:
                return "drizzle-kit push --force applies data-loss changes without review."
        client = any(seg[0] in SQL_CLIENTS or seg[:2] == ["railway", "connect"] for seg in pipeline)
        if client:
            tokens = [t for seg in pipeline for t in seg if not t.startswith("-")]
            reason = destructive_sql(" ".join(clean_sql(t) for t in tokens))
            if reason:
                return reason
    for body in heredoc_bodies(command):
        reason = destructive_sql(clean_sql(body))
        if reason:
            return reason
    return None


def evaluate(command: str, cwd: str, depth: int = 0) -> str | None:
    command = command.replace("\\\n", " ")
    lines = pipelines(command)
    branch = None
    for pipeline in lines:
        for seg in pipeline:
            if seg[0] == "cd" and len(seg) > 1:
                cwd = os.path.join(cwd, os.path.expanduser(seg[1]))
                continue
            if seg[0] == "git" and len(seg) > 2 and seg[1] in {"switch", "checkout"}:
                target = [a for a in seg[2:] if not a.startswith("-")]
                branch = target[0] if target else branch
            if seg[0] in SHELLS and depth < 3:
                script = next((seg[j + 1] for j, a in enumerate(seg[:-1]) if re.fullmatch(r"-[a-z]*c[a-z]*", a)), None)
                if script:
                    reason = evaluate(script, cwd, depth + 1)
                    if reason:
                        return reason
            for check in (lambda s: check_git_push(s, cwd, branch), check_deploy, check_money_api):
                reason = check(seg)
                if reason:
                    return reason
    return check_sql(command, lines)


def command_from(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("command", tool_input.get("cmd", ""))
    if isinstance(raw, list):
        raw = raw[-1] if len(raw) >= 3 and raw[1] in {"-c", "-lc"} else " ".join(raw)
    return raw if isinstance(raw, str) else ""


def harness(payload: dict) -> str:
    forced = os.environ.get("ANDREW_GUARD_HARNESS")
    if forced:
        return forced
    return "codex" if "turn_id" in payload else "claude"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        command = command_from(payload)
        if not command:
            return 0
        reason = evaluate(command, (payload.get("tool_input") or {}).get("workdir") or payload.get("cwd") or os.getcwd())
    except Exception as exc:  # noqa: BLE001
        print(f"andrew-stack guard skipped: {exc}", file=sys.stderr)
        return 0
    if not reason:
        return 0

    if harness(payload) == "codex":
        decision = "deny"
        message = (
            f"andrew-stack guard: {reason} This action is guarded; the hook cannot verify conversation authorization. "
            f"Stop this command, continue independent permitted work, and hand Andrew the exact command if no harness approval route is available:\n{command}"
        )
    else:
        decision = "ask"
        message = f"andrew-stack guard: {reason} Confirm only with applicable explicit authorization or the repo runbook; otherwise stop this action."
    json.dump(
        {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": message,
        }},
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
