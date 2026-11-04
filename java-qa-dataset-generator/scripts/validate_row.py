#!/usr/bin/env python3
"""Validate Java AI Tutor dataset rows (JSONL).

Usage:
  python3 validate_row.py row.jsonl                      # format + quality checks
  python3 validate_row.py --prompt prompt.txt row.jsonl  # also check against the prompt(s)
  python3 validate_row.py --compile row.jsonl            # also compile Java code blocks (needs javac)

prompt.txt may contain several prompt lines; they are matched to rows by id.
Exit code 0 = PASS (warnings allowed), 1 = at least one ERROR.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KEYS = ["id", "type", "category", "difficulty", "language", "messages"]
DIFFICULTIES = {"beginner", "intermediate", "advanced"}
LANGUAGES = {"Java", "Bash", "PowerShell", "Python", "JavaScript", "SQL", "YAML", "General"}
FENCE_TO_LANG = {"java": "Java", "bash": "Bash", "sh": "Bash", "shell": "Bash", "powershell": "PowerShell",
                 "python": "Python", "javascript": "JavaScript", "js": "JavaScript", "sql": "SQL",
                 "yaml": "YAML", "yml": "YAML"}
ALLOWED_FENCE_TAGS = set(FENCE_TO_LANG) | {"xml", "kotlin", "groovy", "properties", "json", "text", "ini", "toml",
                                           "dockerfile", "http", "html", "css", "diff", "csv", "regex", "hcl", "nginx", "c"}
LENGTH = {  # (single-turn min, max, multi-turn min, max) per assistant message
    "beginner": (300, 1200, 250, 1000),
    "intermediate": (500, 2200, 400, 1600),
    "advanced": (800, 3200, 600, 2400),
}
HARD_MIN, HARD_MAX = 150, 4500
FORBIDDEN = [r"great question", r"\bcertainly\b", r"^sure[!,.]", r"as an ai\b", r"i hope this helps",
             r"let me know if", r"happy coding", r"in conclusion", r"\bthe dataset\b", r"\bthis dataset\b"]
BANNED_QUESTIONS = [r"^what is [^?]{1,60} in java\?$", r"how do i use .{1,60} effectively",
                    r"when and how should i use", r"how do i implement '.+' in java"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
FENCE = re.compile(r"^[ \t]*```([^\n`]*)$", re.M)
CODE_BLOCK = re.compile(r"```([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.S)


def parse_prompt(text):
    """Return the expected fields for a prompt line, or None if it isn't one."""
    m = re.search(r'"id":\s*(\d+),\s*"type":\s*"(\w+)",\s*"category":\s*"([^"]+)",\s*"difficulty":\s*"(\w+)"', text)
    if not m:
        return None
    if "(6 messages)" in text:
        msgs = 6
    elif "(4 messages)" in text:
        msgs = 4
    else:
        msgs = 2
    group = "security" if "security tutoring conversation" in text else "java"
    return {"id": int(m.group(1)), "type": m.group(2), "category": m.group(3), "difficulty": m.group(4),
            "messages": msgs, "group": group}


def fence_problems(content):
    errs = []
    fences = FENCE.findall(content)
    if len(fences) % 2 or content.count("```") % 2:
        errs.append("unbalanced ``` code fences")
    else:
        for tag in fences[0::2]:
            tag = tag.strip().lower()
            if not tag:
                errs.append("code block without a language tag")
            elif tag not in ALLOWED_FENCE_TAGS:
                errs.append(f"unusual code fence tag '{tag}'")
    return errs


def compile_java(blocks):
    """Compile complete Java compilation units; return list of (severity, message)."""
    out = []
    if not shutil.which("javac"):
        return [("WARN", "javac not found; Java code was not compiled (review it carefully by hand)")]
    for n, code in enumerate(blocks, 1):
        if not re.search(r"^\s*(public\s+)?(final\s+|abstract\s+|sealed\s+)*(class|record|interface|enum)\s+\w+", code, re.M):
            continue  # fragment: not a full compilation unit
        pub = re.search(r"public\s+(?:final\s+|abstract\s+|sealed\s+)*(?:class|record|interface|enum)\s+(\w+)", code)
        name = pub.group(1) if pub else "Snippet"
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / f"{name}.java"
            src.write_text(code)
            r = subprocess.run(["javac", "-d", d, "-Xlint:none", str(src)], capture_output=True, text=True)
            if r.returncode:
                first = (r.stderr.strip().splitlines() or ["?"])[0]
                missing_dep = re.search(r"package (org|com|io|jakarta|lombok|reactor)\.[\w.]* does not exist", r.stderr)
                sev = "WARN" if missing_dep else "ERROR"
                note = " (external library not on classpath)" if missing_dep else ""
                out.append((sev, f"java block {n} ({name}) does not compile{note}: {first}"))
    return out


def check_row(line, expected=None, do_compile=False):
    errors, warns = [], []
    try:
        row = json.loads(line)
    except json.JSONDecodeError as e:
        return None, [f"invalid JSON: {e}"], []
    if not isinstance(row, dict):
        return None, ["row is not a JSON object"], []

    if list(row.keys()) != KEYS:
        errors.append(f"keys must be exactly {KEYS} in that order, got {list(row.keys())}")
    rid = row.get("id")
    if not isinstance(rid, int) or isinstance(rid, bool) or rid < 1:
        errors.append("id must be a positive integer")
    typ, cat, diff, lang = row.get("type"), row.get("category"), row.get("difficulty"), row.get("language")
    if typ not in ("single_turn", "multi_turn"):
        errors.append(f"type must be single_turn or multi_turn, got {typ!r}")
    if diff not in DIFFICULTIES:
        errors.append(f"difficulty must be one of {sorted(DIFFICULTIES)}, got {diff!r}")
    if lang not in LANGUAGES:
        errors.append(f"language must be one of {sorted(LANGUAGES)}, got {lang!r}")
    if not isinstance(cat, str) or not cat.strip():
        errors.append("category must be a non-empty string")

    msgs = row.get("messages")
    if not isinstance(msgs, list) or not msgs:
        errors.append("messages must be a non-empty list")
        msgs = []
    for i, m in enumerate(msgs):
        if not isinstance(m, dict) or list(m.keys()) != ["role", "content"]:
            errors.append(f"message {i + 1} must have exactly keys role, content")
            continue
        want = "user" if i % 2 == 0 else "assistant"
        if m["role"] != want:
            errors.append(f"message {i + 1} role should be {want}, got {m['role']!r}")
        if not isinstance(m["content"], str) or not m["content"].strip():
            errors.append(f"message {i + 1} content is empty")
        elif m["content"].strip() in ("...", "…"):
            errors.append(f"message {i + 1} content is still the '...' placeholder")
    if msgs and len(msgs) % 2:
        errors.append("conversation must end with an assistant message")
    if typ == "single_turn" and len(msgs) != 2:
        errors.append(f"single_turn must have 2 messages, got {len(msgs)}")
    if typ == "multi_turn" and len(msgs) not in (4, 6):
        errors.append(f"multi_turn must have 4 or 6 messages, got {len(msgs)}")

    if expected:
        for k in ("id", "type", "category", "difficulty"):
            if row.get(k) != expected[k]:
                errors.append(f"{k} must be {expected[k]!r} (from the prompt), got {row.get(k)!r}")
        if len(msgs) != expected["messages"]:
            errors.append(f"prompt asks for {expected['messages']} messages, got {len(msgs)}")

    texts = [m.get("content", "") if isinstance(m, dict) and isinstance(m.get("content"), str) else "" for m in msgs]
    all_text = "\n".join(texts)
    blocks = CODE_BLOCK.findall(all_text)
    tags = [t.lower() for t, _ in blocks]

    # language rule
    group = expected["group"] if expected else None
    if group == "java" and lang != "Java":
        errors.append('Java-group prompt: language must be "Java"')
    if group == "security" or (group is None and lang != "Java"):
        if "java" in tags and lang != "Java":
            errors.append('conversation contains a ```java block, so language must be "Java"')
        elif not blocks and lang in LANGUAGES and lang not in ("General", "Java"):
            errors.append('no code blocks, so language should be "General"')
        elif blocks and "java" not in tags:
            mapped = [FENCE_TO_LANG[t] for t in tags if t in FENCE_TO_LANG]
            if mapped and lang not in mapped:
                warns.append(f"language {lang!r} does not match the code blocks ({', '.join(sorted(set(mapped)))})")

    for i, t in enumerate(texts):
        who = "user" if i % 2 == 0 else "assistant"
        for e in fence_problems(t):
            (errors if "unbalanced" in e else warns).append(f"message {i + 1}: {e}")
        if EMOJI.search(t):
            warns.append(f"message {i + 1}: contains emoji")
        if who == "user":
            first_line = t.strip().splitlines()[0].lower() if t.strip() else ""
            for pat in BANNED_QUESTIONS:
                if re.search(pat, first_line):
                    errors.append(f"message {i + 1}: banned template question ({pat})")
            if len(t) < 20:
                errors.append(f"message {i + 1}: learner message too short ({len(t)} chars)")
            if re.search(r"\b(dataset|as an ai|the tutor)\b", t, re.I):
                errors.append(f"message {i + 1}: learner message mentions dataset/AI/tutor")
        else:
            n = len(t)
            if n < HARD_MIN or n > HARD_MAX:
                errors.append(f"message {i + 1}: assistant length {n} outside hard limits {HARD_MIN}-{HARD_MAX}")
            elif diff in LENGTH:
                lo, hi = LENGTH[diff][:2] if typ == "single_turn" else LENGTH[diff][2:]
                if not (lo * 0.85 <= n <= hi * 1.15):
                    warns.append(f"message {i + 1}: assistant length {n} outside target {lo}-{hi} for {diff}")
            low = t.lower()
            for pat in FORBIDDEN:
                if re.search(pat, low, re.M):
                    errors.append(f"message {i + 1}: forbidden phrase /{pat}/")
            if re.search(r"#{1,2} ", t) and re.search(r"^#{1,2} \S", t, re.M):
                warns.append(f"message {i + 1}: uses a heading larger than ###")

    # multi-turn: follow-up should not repeat the first question
    users = [texts[i].strip().lower() for i in range(0, len(texts), 2)]
    if len(users) != len(set(users)):
        errors.append("a follow-up question repeats an earlier question")

    # security hygiene
    if re.search(r"AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC )?PRIVATE KEY-----", all_text):
        errors.append("contains what looks like a real credential or private key")
    if "// VULNERABLE" in all_text and "// FIXED" not in all_text and "// SAFE" not in all_text:
        warns.append("vulnerable code shown without a // FIXED version")
    if re.search(r'STR\."', all_text):
        errors.append("uses string templates (STR.\"...\"), which were withdrawn in Java 23")
    if re.search(r"\bWebSecurityConfigurerAdapter\b", all_text) and not re.search(r"removed|deprecated|no longer", all_text, re.I):
        errors.append("uses WebSecurityConfigurerAdapter (removed in Spring Security 6) without saying so")
    if re.search(r"import javax\.(persistence|servlet|validation)\.", all_text) and not re.search(r"jakarta", all_text):
        warns.append("uses javax.* imports; Spring Boot 3 / Jakarta EE use jakarta.*")
    if re.search(r"@Test\(expected", all_text) and not re.search(r"JUnit 4", all_text):
        warns.append("@Test(expected=...) is JUnit 4; use assertThrows in JUnit 5")

    if do_compile:
        for sev, msg in compile_java([c for t, c in blocks if t.lower() == "java"]):
            (errors if sev == "ERROR" else warns).append(msg)
    return row, errors, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", help="JSONL file with one row per line ('-' for stdin)")
    ap.add_argument("--prompt", help="file containing the prompt line(s) the rows were generated from")
    ap.add_argument("--compile", action="store_true", help="compile complete Java code blocks with javac")
    args = ap.parse_args()

    text = sys.stdin.read() if args.rows == "-" else Path(args.rows).read_text(encoding="utf-8")
    lines = [l for l in text.splitlines() if l.strip()]
    if lines and lines[0].strip().startswith("```"):
        print("ERROR: file contains a markdown code fence; save only the JSON lines")
        lines = [l for l in lines if not l.strip().startswith("```")]
    prompts = {}
    if args.prompt:
        for pl in Path(args.prompt).read_text(encoding="utf-8").splitlines():
            exp = parse_prompt(pl)
            if exp:
                prompts[exp["id"]] = exp
        if not prompts:
            print("WARN: no prompt line with a JSON skeleton found in --prompt file")

    total_err, seen_ids, seen_q = 0, set(), {}
    for n, line in enumerate(lines, 1):
        row, errors, warns = check_row(line, None, args.compile)
        if row is not None and isinstance(row.get("id"), int):
            exp = prompts.get(row["id"])
            if prompts and not exp:
                errors.append(f"id {row['id']} does not match any prompt")
            if exp:
                row, errors, warns = check_row(line, exp, args.compile)
            if row["id"] in seen_ids:
                errors.append(f"duplicate id {row['id']}")
            seen_ids.add(row["id"])
            q = row["messages"][0]["content"].strip().lower() if row.get("messages") and isinstance(row["messages"][0], dict) else ""
            if q and q in seen_q:
                errors.append(f"same first question as id {seen_q[q]}")
            seen_q.setdefault(q, row["id"])
        label = f"row {n}" + (f" (id {row['id']})" if row and "id" in row else "")
        status = "FAIL" if errors else "PASS"
        print(f"{label}: {status}")
        for e in errors:
            print(f"  ERROR: {e}")
        for w in warns:
            print(f"  WARN:  {w}")
        total_err += len(errors)
    if prompts:
        missing = sorted(set(prompts) - seen_ids)
        if missing:
            print(f"ERROR: no row generated for prompt id(s) {missing}")
            total_err += 1
    print(f"\n{len(lines)} row(s) checked: {'PASS' if total_err == 0 else 'FAIL'} ({total_err} error(s))")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
