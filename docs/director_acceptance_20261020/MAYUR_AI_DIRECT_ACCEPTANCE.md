# AI Direct acceptance

## Implemented

AI Direct remains prompt-first but cannot bypass V4 processing:

1. Select an uploaded dataset and an optional versioned business profile.
2. Selecting a pilot profile loads its versioned default objective into the prompt area.
3. The deterministic planner returns a schema-fingerprint-bound predicate, explanation, unsupported conditions, provider identity, plan hash, and explicit approval requirement.
4. The browser sends the approved plan to the normal job endpoint. The endpoint rejects stale schema fingerprints or a plan that differs from the approved predicate.

The default pilot objectives are descriptive research prompts, not assertions of buyer intent or consent. Custom profile objectives are stored in the tenant-scoped versioned profile definition as `audience_objective`.

## Provider status

No paid provider call was made. Header-only label refinement remains optional and user-triggered. Record-level model review remains deployment-disabled unless separately approved. No private records were transmitted externally.
