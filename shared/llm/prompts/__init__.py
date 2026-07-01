"""Prompt catalogue.

One file per prompt. Each file exports:
    SYSTEM          — the system message string (static)
    build_user(...) — builds the user message from runtime args

Usage:

    from shared.llm.prompts import score_listing as prompt
    messages = [
        {"role": "system", "content": prompt.SYSTEM},
        {"role": "user",   "content": prompt.build_user(profile, listing)},
    ]
    out = llm.invoke(messages, json_mode=True)

Keeping prompts in their own module means:
- Tweaking a prompt is one file change, no provider code touched.
- The prompts are diff-able + reviewable as text, not buried in code.
- The orchestration in `standard.py` reads as "what to do", not "what to say".
"""
