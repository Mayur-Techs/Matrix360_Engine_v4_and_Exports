# Render deployment status

**NOT DEPLOYED.** No Render account, database, private object store or deployment approval was supplied, and the current local filesystem storage adapter must not be placed on an ephemeral Render filesystem for client data.

Before a Render Blueprint can be considered deployable, implement and verify a Postgres metadata adapter, private S3/R2-or-equivalent storage adapter, signed downloads, production auth, encrypted configuration and worker health/readiness. The API and worker are already separated in `docker-compose.yml`, which is the intended service split for a future approved cloud build.

