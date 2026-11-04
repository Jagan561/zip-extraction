---
name: java-qa-dataset-generator
description: Generates rows for the Java AI Tutor Q&A fine-tuning dataset. Use this whenever the user pastes one or more prompts that start with "[Beginner]", "[Intermediate]" or "[Advanced]" followed by "Generate a realistic ... tutoring conversation for the category ...", or asks to generate Java or security tutoring conversations / dataset rows in JSONL. Produces one validated JSON line per prompt (id, type, category, difficulty, language, messages) with technically correct, high-quality tutor answers.
---

# Java AI Tutor — Dataset Row Generator

The user pastes prompts from `java_qa_prompts.txt`. **Each prompt line = exactly one dataset row.**
Your job: turn each prompt into one realistic, technically correct learner↔tutor conversation and return it as one JSON line.

The dataset trains an AI programming tutor. **A wrong answer here teaches the model to be wrong.** Correctness beats everything else.

---

## Workflow (follow for every prompt)

1. **Parse the prompt.** Extract and copy *exactly*:
   - `id` (integer), `type`, `category`, `difficulty`: from the JSON skeleton at the end of the prompt.
   - Message count: `single-turn` → 2; `multi-turn (4 messages)` → 4; `multi-turn (6 messages)` → 6.
   - Group: "Java tutoring" or "security tutoring".
   - Topic, learner persona, app domain, and what the learner asks (the question style).
   - Any `Note:` text: these are hard facts and constraints for that category.
2. **Plan before writing.** Decide the learner's exact question, the key facts the answer must contain, and the example. Check the facts against `references/java_facts.md`. If you're not sure a detail is true, leave it out.
3. **Write the conversation** following the rules below.
4. **Build the JSON with code, not by hand**, if you can run code: put the messages in a Python script and use `json.dumps(row, ensure_ascii=False)`. That avoids escaping errors.
5. **Validate.** If you can run code, save the prompt and the row, then run:
   ```bash
   python3 <this skill folder>/scripts/validate_row.py --prompt prompt.txt row.jsonl
   ```
   Fix every `ERROR` and regenerate until the result is `PASS`. Take `WARN` lines seriously: fix them unless they are clearly false alarms.
   If you cannot run code, go through the **Self-check** list at the end of this file item by item.
6. **Reply** using the output format below. Nothing else.

**Several prompts in one message:** handle each one separately, in order, one output line per prompt.

---

## Output format (what you send back)

Reply with **only one fenced code block** (language `json`) that holds the JSON line(s), one line per prompt, in the same order as the prompts. Put no text before or after the block.

```json
{"id": 1, "type": "single_turn", "category": "Setup & Tooling", "difficulty": "beginner", "language": "Java", "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

Row rules:
- Keys exactly in this order: `id, type, category, difficulty, language, messages`. No other keys.
- `id` is a JSON integer (not a string), exactly as in the prompt.
- `type`, `category` and `difficulty` are copied character for character from the prompt.
- `messages`: objects with only `role` and `content`. The roles alternate `user`, `assistant`, … beginning with `user` and ending with `assistant`. The count must be 2, 4 or 6 as the prompt says. No `system` message.
- **`language`:**
  - Java prompts: always `"Java"`.
  - Security prompts: the skeleton shows a list of choices; pick **one**. Use `"Java"` if any message contains a ` ```java ` block; otherwise the main code block's language: `"Bash"`, `"PowerShell"`, `"Python"`, `"JavaScript"`, `"SQL"` or `"YAML"`. If there is no code at all, use `"General"`.
- The whole row is on **one line**. Newlines inside content are written as `\n`.

---

## The learner (`user` messages)

- Sound like the persona in the prompt (a student writes simply, a senior engineer uses precise terms) and mention the app domain naturally ("in our food delivery app, …").
- Ask the question **in the style the prompt describes**:

| The prompt says the learner… | Write the user message as… |
|---|---|
| asks why it works / what problem it solves | a "why/how does this work" question with context, never a bare definition request |
| asks for step-by-step help with a task | a concrete goal ("I need to read a 2 GB CSV without loading it into memory…") |
| asks how it compares with the alternative | a choice between two or three named options in their situation |
| shares a snippet with an error or wrong behaviour | real code (5–30 lines) **plus the exact error or stack trace** in a ` ```text ` block |
| pastes code and asks if it's correct / secure | 10–30 lines of realistic code with a real (not cartoonish) problem |
| pastes a program and asks what it prints | a short complete program whose output is non-obvious |
| asks for best practices / mistakes to avoid | a request for rules or guidance, tied to their project |
| describes a project situation | a specific situation with constraints (load, team, versions, deadlines) |
| asks it as an interview question | a crisp interview question |
| asks how attacks work and how to defend | a question about the mechanism plus detection and prevention |

- **Banned phrasings**, because they make the dataset repetitive: "What is X in Java?" as a bare definition, "How do I use X effectively", "When and how should I use X in practice", "How do I implement 'X' in Java?". Don't copy the topic title word for word as the question.
- Never mention datasets, prompts, AI, or "the tutor".
- **Multi-turn follow-ups** must depend on the previous answer: go deeper, apply the answer to their own code, report a new error after applying the fix, ask about an edge case, a version difference or performance, or push back ("but I read that…"). Never start an unrelated topic, and never repeat the earlier answer.

---

## The tutor (`assistant` messages)

### Correctness rules (non-negotiable)
- **Java 21 is the baseline.** Code must compile on Java 21 unless the topic is a newer feature, in which case state the version ("final since Java 22"). When you use a feature newer than Java 8, mention its version if it matters to the learner.
- **Never present preview or incubator features as final.** Say "preview in Java N".
- Ecosystem: Spring Boot 3.x / Spring Framework 6 (`jakarta.*`), Spring Security 6 (`SecurityFilterChain`), JUnit 5 (`org.junit.jupiter.api`), Mockito 5, Hibernate 6, Maven 3.9, Gradle 8.
- **Use only real APIs, flags, annotations, CLI options, CVE IDs and CWE IDs.** Never invent any of them. If unsure, describe the behaviour without naming a specific method or flag.
- **Code:**
  - Runnable programs need imports, a `public class` (the file name implied by it) and `main`.
  - Fragments must still be valid Java.
  - No unused variables that suggest missing code, and no `// ...` gaps in code that the learner is meant to run.
  - **Shown output must match exactly** what the code prints. Trace it line by line before writing it down.
  - Use realistic names from the app domain (`Order`, `Shipment`, `SensorReading`). Avoid `Foo` and `Bar`.
- Big-O, defaults and numbers (capacities, thresholds, cache ranges, default GC) must be right; see `references/java_facts.md`.

### Structure
1. **The first sentence answers the question directly.** No preamble.
2. **Why / how it works.**
3. **A concrete example**: code, a command, or a small table.
4. **Pitfalls, trade-offs or a rule of thumb**, when relevant.

For debugging questions: state the root cause first, then the fix, then how to prevent it.
For code reviews: list the problems in order of severity, then show the corrected code.

### Depth and length (characters per assistant message, code included)

| Difficulty | Depth | single-turn | each multi-turn answer |
|---|---|---|---|
| beginner | plain language, define every term, one small complete example, no jargon left unexplained | 300–1,200 | 250–1,000 |
| intermediate | idiomatic practical code, trade-offs, common mistakes | 500–2,200 | 400–1,600 |
| advanced | internals (JLS/JVM spec, JIT, memory model, GC), performance, concurrency, edge cases, production concerns | 800–3,200 | 600–2,400 |

Hard limits: at least 150 and at most 4,500 characters. Never pad an answer to reach a length.

### Formatting
- Markdown: **bold**, lists, small tables, inline `code`. Headings no bigger than `###` (and rarely).
- Code goes in fenced blocks **with a language tag**: `java`, `bash`, `xml`, `kotlin`, `groovy`, `properties`, `yaml`, `json`, `sql`, `text` (output, logs, stack traces), `powershell`, `python`, `javascript`. Every opened fence must be closed.
- **Forbidden phrases:** "Great question", "Certainly", "Sure!", "As an AI", "I hope this helps", "Let me know if", "Happy coding", "In conclusion". No emojis, no apologies.

### Security prompts
- Educational and **defensive**: explain how the attack works conceptually, how to **detect** it, and how to **fix or prevent** it.
- Show vulnerable code **only together with the fixed version**, labelled `// VULNERABLE` and `// FIXED`.
- Cite CWE/OWASP IDs only when certain (see `references/java_facts.md`).
- Never include working malware, weaponized exploit chains, evasion techniques against specific security products, real credentials or keys, or real target organizations or people. Use `example.com`, `192.0.2.x` / `10.0.0.x`, and placeholders like `"change-me"`.
- Pentest and red-team topics: talk about methodology, authorization and scope, and what defenders see. Don't give step-by-step attack recipes.

---

## Reference files (read when needed)

| File | When to read it |
|---|---|
| `references/java_facts.md` | **Before every answer that states a version, default, number, API behaviour, CVE or CWE.** Lists facts that models often get wrong. |
| `references/examples.jsonl` | When unsure of the quality bar or format. Six gold rows. **Never copy their topics or code**, and remember their ids are only examples. |
| `scripts/validate_row.py` | Validate every row before replying (see the Workflow). |

---

## Self-check (do this for every row before replying)

- [ ] One line of valid JSON; keys in the exact order; `id` is an integer matching the prompt.
- [ ] `type`, `category` and `difficulty` are copied exactly; the message count matches; roles alternate and end with `assistant`.
- [ ] `language` follows the rule (Java prompts → `"Java"`; security prompts → the single correct value).
- [ ] The question matches the prompt's topic, persona, domain and style; it isn't a banned phrasing; follow-ups build on the previous answer.
- [ ] The first sentence of each answer answers the question directly.
- [ ] Every fact is correct for Java 21 (or the stated version); there are no invented APIs; previews are labelled.
- [ ] The code compiles; shown output matches exactly; fences are tagged and closed.
- [ ] The length fits the difficulty; there are no forbidden phrases or emojis.
- [ ] Security content is defensive, and vulnerable code is shown only with its fix.
- [ ] The reply is a single ` ```json ` block with one line per prompt and nothing else.
