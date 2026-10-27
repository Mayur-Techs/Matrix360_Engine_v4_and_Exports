# People-First Entity & Filter Contract

**Workstream Owner:** Mayur (`Mayur-Techs`)  
**Standard:** People-First Intelligence & Generalized Entity Schema  
**Date:** 27 October 2026  

---

## 1. Generalized Entity Schema

The platform represents audience intelligence through a generalized multi-entity model:

```
[Person] ──(Affiliation / Role)──> [Organization]
   │                                     │
   ▼                                     ▼
[Evidence / Source]               [Operating Location]
   │                                     │
   └───────────────► [QualificationAssessment]
                            │
                            ▼
                   [AudiencePlan / Snapshot]
```

### Invariants:
1. **Multiple Verified People per Company:** Deduplication is strictly entity-aware. Two decision-makers at the same company (e.g. `Aarav Sharma (MD)` and `Diya Sen (CFO)` at `apex-corp.in`) retain distinct `lead_id`s and separate profile records.
2. **Named-Person Gaps (`PERSON_NOT_OBSERVED`):** When an organization is discovered without a named decision-maker on public pages, the record is classified as `ORGANIZATION_CANDIDATE` with `person_name = "PERSON_NOT_OBSERVED"`. The engine never invents a fictional executive.
3. **Purchasing Authority & Financial Intent:** Job titles alone do not prove budget or affluence. Commercial intent is modeled as an evidence-backed hypothesis requiring engagement.

---

## 2. Three Editable Criteria Cards

Each client workspace maintains three distinct criteria definitions:

1. **Discovery Criteria Card:**
   - Search parameters, geographic scope, entity mode (`PERSON` vs `ORGANIZATION`), and source categories (Web Dorks, Google Maps, Corporate Registries).
2. **Qualification Criteria Card:**
   - Must-have evidence anchors (e.g., active phone, physical address, named executive, valid domain).
3. **AI Assessment Criteria Card:**
   - Sector alignment, role seniority heuristics, geographic affinity rules (e.g. Chandannagar native roots), and uncertainty flags.

---

## 3. Dynamic Client Generalization

Verified across 6 distinct client archetypes:
1. `lakhotia`: B2B Industrial logistics & warehousing (Howrah/Hooghly).
2. `shree`: B2C Premium residential apartments (Chandannagar professionals: Doctors, CAs, Advocates).
3. `vrindavan`: B2C Villa plots & community living (Kalyani Expressway corridor).
4. `matrix360_advisory`: B2B Corporate promoters & CFOs (₹25 Cr+ turnover).
5. `apex_industrial_fleet`: B2B Logistics fleet heads & transport operators.
6. `zenith_clinical_research`: B2B/B2C Clinical oncology investigators & genomic trial heads (non-industrial test archetype).
