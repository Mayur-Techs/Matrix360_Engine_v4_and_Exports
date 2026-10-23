"""
50,000-Lead Scale Engine & AI Business/Persona Synthesizer (`scale_50k_engine.py`)
"""
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TargetBusinessArchetype:
    archetype_name: str
    why_they_need_us: str
    facility_indicators: List[str]
    typical_scale: str


@dataclass
class InterestedPersonPersona:
    role_title: str
    department: str
    buying_trigger: str
    priority_level: str


@dataclass
class CampaignBlueprint:
    campaign_title: str
    target_scale: int
    ai_provider_used: str
    search_mode: str
    business_archetypes: List[TargetBusinessArchetype]
    interested_people_roles: List[InterestedPersonPersona]
    positive_qualification_filters: List[str]
    negative_exclusion_filters: List[str]
    location_hierarchy_rules: List[str]
    estimated_monthly_infra_cost_usd: str


class BusinessAndPersonaSynthesizer:
    @classmethod
    def synthesize_blueprint(
        cls,
        prompt: str,
        target_scale: int = 5000,
        ai_provider: str = "openai",
        has_search_api_key: bool = False,
    ) -> CampaignBlueprint:
        p_low = (prompt or "").lower()
        search_mode = "Hybrid (API + Multi-Vector OSINT)" if has_search_api_key else "Keyless Multi-Vector OSINT (No Search API Required)"

        if any(w in p_low for w in ("howrah", "kolkata", "hooghly", "warehouse", "industrial", "manufacturing", "lakhotia", "factory", "foundry")):
            archetypes = [
                TargetBusinessArchetype(
                    archetype_name="Heavy Engineering, Forging & Foundry Manufacturers",
                    why_they_need_us="Expanding production bays, machine shops, and heavy raw-material storage near NH-6 / NH-2 corridors.",
                    facility_indicators=["Works / Plant address in Howrah, Hooghly, or Kolkata", "ISO 9001 / BIS / Factory Act license", "MTPA capacity or furnace/machining specs"],
                    typical_scale="MSME (Micro/Small/Medium) to Mid-Cap Industrial Units"
                ),
                TargetBusinessArchetype(
                    archetype_name="3PL Warehousing, Cold Chain & Freight Hub Operators",
                    why_they_need_us="Seeking Grade-A built-to-suit (BTS) warehouses, pallet storage, and multi-axle truck docking bays near Sankrail, Dhulagarh, and Dankuni.",
                    facility_indicators=["3PL / Fulfillment hub footprint", "Cold storage (+4°C to -25°C) or CFS yard", "Fleet operations & dock doors"],
                    typical_scale="Regional & National Supply-Chain Operators"
                ),
                TargetBusinessArchetype(
                    archetype_name="Polymer, Packaging, Agro-Processing & Chemical Units",
                    why_they_need_us="Requiring pollution-board compliant industrial plots and high-ceiling processing sheds with continuous power.",
                    facility_indicators=["Blown film / extrusion / agro mill plant", "WBPCB / FSSAI / GSTIN-19 registration", "Dedicated dispatch & storage sheds"],
                    typical_scale="Growing B2B Producers & Exporters"
                ),
            ]
            personas = [
                InterestedPersonPersona(
                    role_title="Managing Director / Promoter / Managing Partner",
                    department="Executive Leadership",
                    buying_trigger="Approves capital expenditure for new industrial plots, plant expansion, and long-term lease commitments.",
                    priority_level="Primary Decision-Maker"
                ),
                InterestedPersonPersona(
                    role_title="Plant Head / VP Operations / Works Manager",
                    department="Manufacturing & Plant Operations",
                    buying_trigger="Experiences floor-space bottlenecks, power/logistics constraints, and initiates new unit requirements.",
                    priority_level="High-Intent Champion"
                ),
                InterestedPersonPersona(
                    role_title="Head of Supply Chain, Warehousing & 3PL Logistics",
                    department="Logistics & Distribution",
                    buying_trigger="Procures regional distribution hubs, mother warehouses, and NH-16/NH-2 transit storage.",
                    priority_level="Primary Decision-Maker"
                ),
                InterestedPersonPersona(
                    role_title="CFO / Company Secretary / Head of Procurement & Projects",
                    department="Finance, Compliance & Projects",
                    buying_trigger="Evaluates commercial lease terms, statutory clearances, and vendor/infrastructure onboarding.",
                    priority_level="Commercial Gatekeeper"
                ),
            ]
            pos_filters = [
                "Verified official company domain with active Plant, Factory, Works, Foundry, or Warehouse operations",
                "Operating presence in Howrah (Sankrail, Dhulagarh, Uluberia, Liluah), Hooghly (Dankuni, Baidyabati), or Greater Kolkata",
                "Published corporate phone, business email, and verifiable street/estate address",
                "MSME (Udyam), ISO, BIS, FSSAI, or West Bengal GSTIN (19...) / CIN (...WB...) when published"
            ]
            neg_filters = [
                "Pure consumer retail stores, fashion outlets, shopping malls, and multiplexes",
                "Restaurants, buffet chains, food delivery apps, and hospitality venues",
                "Residential apartment projects and real-estate brokerage agencies",
                "Third-party B2B directories (IndiaMART, Justdial, ZaubaCorp) and consumer broadband ISPs"
            ]
            loc_rules = [
                "Strictly separate Plant/Factory and Warehouse site addresses from Corporate Head Offices",
                "Flag regional offices without an evidenced local plant/warehouse for human Review rather than guessing",
                "Keep Company Phone/Email strictly separate from Named Decision-Maker Phone/Email"
            ]
            title = "Industrial Manufacturers, Engineering Works & 3PL Warehousing Buyers"
        else:
            words = [w.strip(".,;:()") for w in prompt.split() if len(w) > 3]
            core = " ".join(words[:5]) or "Target B2B Sector"
            archetypes = [
                TargetBusinessArchetype(
                    archetype_name=f"Core Operating Companies in {core}",
                    why_they_need_us="Direct operational fit with the product, facility, or B2B service described in your prompt.",
                    facility_indicators=["Active commercial/industrial operations", "Published product or service catalog", "Verified physical operating address"],
                    typical_scale="SMB to Enterprise B2B Organizations"
                ),
                TargetBusinessArchetype(
                    archetype_name="High-Growth Regional Operators & Supply-Chain Partners",
                    why_they_need_us="Expanding regional footprint and actively onboarding new infrastructure or B2B vendors.",
                    facility_indicators=["Multi-location footprint", "Active hiring or expansion notices", "Direct departmental contact channels"],
                    typical_scale="Mid-Market Regional Leaders"
                ),
            ]
            personas = [
                InterestedPersonPersona(
                    role_title="Founder / Managing Director / CEO",
                    department="Executive Leadership",
                    buying_trigger="Final sign-off on strategic partnerships, new facilities, and core B2B investments.",
                    priority_level="Primary Decision-Maker"
                ),
                InterestedPersonPersona(
                    role_title="VP Operations / Head of Infrastructure & Facilities",
                    department="Operations",
                    buying_trigger="Owns day-to-day operational efficiency and vendor/site selection.",
                    priority_level="High-Intent Champion"
                ),
                InterestedPersonPersona(
                    role_title="Head of Procurement / Commercial Director",
                    department="Procurement & Commercial",
                    buying_trigger="Manages vendor qualification, RFPs, and commercial contracting.",
                    priority_level="Commercial Gatekeeper"
                ),
            ]
            pos_filters = [
                f"Official company website matching core focus: {core}",
                "Verified operating address and active B2B product/service evidence",
                "Published business email, phone number, or named leadership contacts"
            ]
            neg_filters = [
                "Third-party aggregator directories, social profiles, and parked domains",
                "Unrelated consumer retail, hospitality, or residential listings"
            ]
            loc_rules = [
                "Preserve distinction between operating sites and registered offices",
                "Never merge generic company emails with personal decision-maker contacts"
            ]
            title = f"B2B Buyer & Decision-Maker Discovery: {core}"

        return CampaignBlueprint(
            campaign_title=title,
            target_scale=target_scale,
            ai_provider_used=ai_provider,
            search_mode=search_mode,
            business_archetypes=archetypes,
            interested_people_roles=personas,
            positive_qualification_filters=pos_filters,
            negative_exclusion_filters=neg_filters,
            location_hierarchy_rules=loc_rules,
            estimated_monthly_infra_cost_usd="$0–$7/mo (SQLite WAL + Open-Source Async Workers)"
        )


class SQLiteWALCheckpointStore:
    def __init__(self, db_path: str = "/tmp/vanguard_50k_checkpoint.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS domain_queue (
                    domain_hash TEXT PRIMARY KEY,
                    canonical_domain TEXT UNIQUE,
                    discovery_vector TEXT,
                    status TEXT DEFAULT 'PENDING',
                    qualification_status TEXT DEFAULT '',
                    confidence_score REAL DEFAULT 0.0,
                    payload_json TEXT DEFAULT '{}',
                    updated_at REAL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def hash_domain(domain: str) -> str:
        return hashlib.sha256(domain.strip().lower().encode("utf-8")).hexdigest()[:24]

    def enqueue_domains(self, domains: List[Dict[str, str]]) -> int:
        conn = sqlite3.connect(self.db_path)
        inserted = 0
        now = time.time()
        try:
            for item in domains:
                dom = (item.get("canonical_domain") or "").strip().lower()
                if not dom:
                    continue
                d_hash = self.hash_domain(dom)
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO domain_queue
                    (domain_hash, canonical_domain, discovery_vector, status, updated_at)
                    VALUES (?, ?, ?, 'PENDING', ?)
                    """,
                    (d_hash, dom, item.get("vector", "KEYLESS_OSINT"), now),
                )
                inserted += cur.rowcount
            conn.commit()
        finally:
            conn.close()
        return inserted

    def save_qualified_lead(self, domain: str, qual_status: str, conf: float, lead_dict: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        now = time.time()
        try:
            d_hash = self.hash_domain(domain)
            conn.execute(
                """
                INSERT INTO domain_queue
                (domain_hash, canonical_domain, discovery_vector, status, qualification_status, confidence_score, payload_json, updated_at)
                VALUES (?, ?, ?, 'COMPLETED', ?, ?, ?, ?)
                ON CONFLICT(domain_hash) DO UPDATE SET
                    status='COMPLETED',
                    qualification_status=excluded.qualification_status,
                    confidence_score=excluded.confidence_score,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (d_hash, domain, lead_dict.get("extraction_method", "HYBRID"), qual_status, conf, json.dumps(lead_dict), now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, int]:
        conn = sqlite3.connect(self.db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM domain_queue").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM domain_queue WHERE status='COMPLETED'").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM domain_queue WHERE status='PENDING'").fetchone()[0]
            return {"total_tracked": total, "completed": completed, "pending": pending}
        finally:
            conn.close()
