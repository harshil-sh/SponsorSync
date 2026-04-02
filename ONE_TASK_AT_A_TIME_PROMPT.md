# One-Task-at-a-Time Execution Prompt

Use this prompt with your coding assistant to complete exactly one task from `DEVELOPMENT_TASK_LIST.md` at a time.

---

## Prompt (Copy/Paste)

```text
You are implementing the SponsorSync backlog one task at a time.

Context files:
- IMPLEMENTATION_PLAN.md
- DEVELOPMENT_TASK_LIST.md

Execution rules:
1) Complete ONLY this task in this run: <PASTE EXACT TASK ID + TASK TEXT>
   Example: "Epic 1 → 1.3 Salary parsing utility (annualize salary in GBP)"
2) Do not start any other task, even if related.
3) If prerequisites are missing, do the minimum required setup and clearly label it as prerequisite work for this task.
4) Keep changes small and focused.
5) Add or update tests strictly for the selected task.
6) Run relevant checks and report exact commands + results.
7) Update DEVELOPMENT_TASK_LIST.md by marking only the completed task as [x] (leave all others unchanged).
8) Create a commit with message format:
   feat(task): <short description>
9) Provide a short completion report with:
   - What changed
   - Files touched
   - Tests run
   - Any follow-up risks/blockers

Quality bar:
- Production-ready code
- Clear naming and type-safe structures
- No hardcoded secrets
- Backward-compatible changes unless explicitly required

If task scope is ambiguous, stop and ask one concise clarification question before coding.
```

---

## How to Use

1. Pick one unchecked item from `DEVELOPMENT_TASK_LIST.md`.
2. Replace `<PASTE EXACT TASK ID + TASK TEXT>` with that exact line.
3. Submit the prompt.
4. Review output and tests.
5. Merge/commit.
6. Repeat for next unchecked task.

---

## Example Filled Prompt

```text
You are implementing the SponsorSync backlog one task at a time.

Context files:
- IMPLEMENTATION_PLAN.md
- DEVELOPMENT_TASK_LIST.md

Execution rules:
1) Complete ONLY this task in this run: Epic 1 → 1.3 Salary parsing utility (annualize salary in GBP)
2) Do not start any other task, even if related.
3) If prerequisites are missing, do the minimum required setup and clearly label it as prerequisite work for this task.
4) Keep changes small and focused.
5) Add or update tests strictly for the selected task.
6) Run relevant checks and report exact commands + results.
7) Update DEVELOPMENT_TASK_LIST.md by marking only the completed task as [x] (leave all others unchanged).
8) Create a commit with message format:
   feat(task): salary parsing utility for UK annual GBP normalization
9) Provide a short completion report with:
   - What changed
   - Files touched
   - Tests run
   - Any follow-up risks/blockers

Quality bar:
- Production-ready code
- Clear naming and type-safe structures
- No hardcoded secrets
- Backward-compatible changes unless explicitly required

If task scope is ambiguous, stop and ask one concise clarification question before coding.
```
