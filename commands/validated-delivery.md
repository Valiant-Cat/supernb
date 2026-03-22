# validated-delivery

```text
Execution profile: validated-delivery
Goal: <complete one validated delivery batch from the approved plan>
Context:
- repository: <url or local path>
- platform: <target platform if relevant>
- stack: <frameworks or languages>
- initiative id: <existing initiative id if known>
- constraints: <test, review, release, or branch constraints>
Output:
- execute exactly one validated batch with tests first
- update affected initiative artifacts, verification evidence, and release-readiness inputs
- keep the implementation depth aligned with a 10M-DAU-grade product bar rather than a thin proof of concept
- treat fake features, placeholders, stubs, and no-op flows as incomplete work rather than shipped delivery
- if the batch adds or materially changes a visible user-facing feature, land a real surfaced entry and use impeccable to settle unresolved entry placement before claiming completion
- externalize user-facing copy and run the hardcoded-copy check instead of hardcoding strings in product code
- for Claude Code prompt-first planning or delivery, start and honor the Ralph Loop contract instead of stopping on self-judged completion
- commit the verified batch and return evidence for certification
```
