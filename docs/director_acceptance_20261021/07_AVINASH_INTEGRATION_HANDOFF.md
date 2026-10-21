# 07 — Avinash integration handoff

Status: READY FOR REVIEW; no live integration attempted.

The contract is already documented in `docs/integrations/AVINASH_AUDIENCE_HANDOFF.md` and `docs/integrations/audience-api-v1.openapi.yaml`.

Required sequence: Avinash browser -> Avinash authenticated backend -> signed Matrix audience gateway. The browser must never carry the service secret or choose a tenant. The gateway binds a server-side workspace assertion using HMAC over method, path, workspace, timestamp and nonce; Matrix maps it to an internal tenant key and rejects absent, expired, replayed and mismatched assertions.

No Supabase, Cloudflare, Render, Vercel, Avinash repository, CRM data or hosted migration was contacted or changed. Production handoff remains blocked on Director-selected environments, server-only secret provisioning, RLS/object storage/queue design review, staged synthetic smoke test and rollback ownership.
