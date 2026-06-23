# AI Gateway — multi-provider, free-tier, auto-rotate on rate-limit

Design doc (implemented in Phase 4). Keep in sync with the implementation under `backend/app/ai/gateway/`.

## Goals
- Free tier only (Groq + Gemini). Never block the hot path.
- Rotate by (provider, account) on 429/quota-exhaustion. Downgrade model when needed. Cache hard. Degrade gracefully.

## Quota truths (don't mis-design)
- Groq: quota is per-ORGANIZATION, not per key → many keys in one org = useless.
- Gemini: quota is per-PROJECT, not per key. Enabling billing = that project loses free tier.
- => Real "key rotation" = rotating across MULTIPLE PROVIDERS and MULTIPLE ACCOUNTS/PROJECTS (mind each ToS).

## Architecture
1) Single OpenAI-compatible client (openai SDK; swap base_url + api_key per account).
   - Groq:   base_url=https://api.groq.com/openai/v1
   - Gemini: base_url=https://generativelanguage.googleapis.com/v1beta/openai/
2) Account pool (config): each account = {name, provider, base_url, api_key, models[], limits{rpm,tpm,rpd}}.
3) Rate tracker: local token-bucket per (account, model) seeded from limits; ALSO honor runtime headers
   429 retry-after + x-ratelimit-* → mark account "cooling" until reset (headers are the source of truth).
4) Queue + concurrency limiter: free RPM is low (Groq ~30, Gemini ~15) → enqueue, cap concurrency, smooth bursts.
   AI tasks run on a background worker; UI shows "analyzing…".
5) Routing policy per task (quality→cheap), fallback across provider/account:
   triage:  [groq:llama-3.3-70b-versatile, gemini:gemini-2.5-flash, groq:llama-3.1-8b-instant]
   nl2sql:  [gemini:gemini-2.5-flash, groq:llama-3.3-70b-versatile]
   report:  [gemini:gemini-2.5-flash, groq:openai/gpt-oss-120b]
   chat:    [groq:llama-3.1-8b-instant, gemini:gemini-2.5-flash-lite]
6) Cache: key = sha256(task + model_family + content). Hit → return immediately, no quota spent.
7) Circuit breaker per provider: consecutive errors → open circuit, skip during cooldown.
8) Structured output: response_format={"type":"json_object"} + JSON schema injected into system prompt;
   parse + validate (jsonschema); on failure → one repair-retry ("return valid JSON per schema, no extra text").
9) Privacy policy: tasks flagged sensitive=true → FORBIDDEN to route via Gemini free (train policy). Groq only
   (or a paid account if present). Strip secrets from every prompt before sending.
10) Ledger: log tokens in/out per provider/account/task → /metrics + usage table in UI.

## Account selection algorithm (condensed)
for provider_model in routing[task]:
    for account in accounts(provider_model) sorted by (cooling?, RPD-remaining desc):
        if breaker_open(account): continue
        if not bucket_ok(account, est_tokens): continue
        try: resp = call(account, model, ...); update_buckets_from_headers(resp); return resp
        except RateLimited(retry_after): mark_cooling(account, retry_after); continue
        except ProviderError: breaker_record(account); continue
raise NoCapacity  # final fallback: "AI busy, try later" + push task to retry queue

## NL→SQL safety constraints (mandatory)
- Force the model to return a single SELECT + param list.
- Parse with sqlglot → BLOCK if INSERT/UPDATE/DELETE/ALTER/DROP/ATTACH/SYSTEM or multiple statements.
- Force-append LIMIT (e.g. 1000) if missing. Run with a ClickHouse read-only role.
- Show the SQL to the user for approval before execution.

See `PROMPT_vibecode_sentinel_platform.md` Appendix B for the full `alert_triage` JSON schema and triage system prompt.
