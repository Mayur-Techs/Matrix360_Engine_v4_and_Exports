"""50-Persona Red-Team & Chaos QA Suite for Matrix 360 Unified Platform.

Simulates 50 distinct adversarial, edge-case, security, and non-technical user personas
attempting to break the Alias Engine, Currency/Affluence Parser, SSRF Guard, Crawler,
Filter DSL, and Production Lead Vault.
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

try:
    from lead_discovery.agents import ContactExtractionAgent, DomainDiscoveryAgent, PromptFilterAgent, QualificationAgent
    from lead_discovery.discovery_zero_api import KeylessSearchRotator, ObfuscatedContactDecoder
    from lead_discovery.security import SSRFGuard, WebhookSigner
    from lead_discovery.verified_pilot_data import PILOT_RECORDS
except ImportError:
    from agents import ContactExtractionAgent, DomainDiscoveryAgent, PromptFilterAgent, QualificationAgent
    from discovery_zero_api import KeylessSearchRotator, ObfuscatedContactDecoder
    from security import SSRFGuard, WebhookSigner
    from verified_pilot_data import PILOT_RECORDS
from engine_v5.agentic_company_qualifier import (
    evaluate_vehicle_profile,
    generate_multichoice_company_filters,
    parse_inr_amount,
    qualify_and_score_lead,
)
from engine_v5.semantic_alias_agent import SemanticAliasAgent
from engine_v5.unified_pipeline import ProductionLeadVault, convert_crawler_record_to_v4_v5_row
from services.worker.exporter import safe_cell


class Test50RedTeamPersonas(unittest.TestCase):
    def setUp(self) -> None:
        self.alias_agent = SemanticAliasAgent()

    def test_personas_01_to_15_adversarial_alias_headers(self) -> None:
        """Personas 1-15: Accountants, regional clerks, and ERP exports with 15 tricky header formats."""
        cases = [
            ("\ufeffKarta_Full_Naam", "name"),
            ("Customer Full Name (As per PAN)", "name"),
            ("Authorized Signatory / Promoter", "name"),
            ("M/S Establishment Legal Title", "company"),
            ("Company / Firm Legal Title", "company"),
            ("Sanstha_Registered_Entity", "company"),
            ("Contact Person Mobile_1", "phone"),
            ("Primary WhatsApp Cell No.", "phone"),
            ("Official Corporate Email ID", "email"),
            ("Turnover (in Rs. Cr)", "annual_turnover"),
            ("Audited_Topline_FY26", "annual_turnover"),
            ("Declared_ITR_Income_PA", "personal_income"),
            ("Net Worth / Wealth Band", "personal_income"),
            ("Car / Four-Wheeler Owned", "vehicle_model"),
            ("Factory / Plant Location City", "city"),
        ]
        for raw_header, expected in cases:
            with self.subTest(raw_header=raw_header):
                res = self.alias_agent.resolve_header(raw_header)
                self.assertEqual(res.canonical_field, expected, f"Failed on {raw_header}: got {res.canonical_field}")

    def test_personas_16_to_25_messy_indian_currency_and_numbers(self) -> None:
        """Personas 16-25: Weird currency formats, attached units, periods in 'Rs.', negatives, and garbage."""
        cases = [
            ("₹1.2Cr", 12_000_000),
            ("Rs. 4,50,00,000", 45_000_000),
            ("25L", 2_500_000),
            ("80 Lakhs/yr", 8_000_000),
            ("INR 15.5 Crores", 155_000_000),
            ("₹ 95 Lac", 9_500_000),
            ("(₹ 5 Crore)", 0),  # Accounting negative rejected safely
            ("-10 Lakh", 0),     # Negative rejected safely
            ("N/A / Unknown", 0),
            ("", 0),
        ]
        for raw_val, expected in cases:
            with self.subTest(raw_val=raw_val):
                self.assertEqual(parse_inr_amount(raw_val), expected)

    def test_personas_26_to_35_ssrf_and_security_pen_testers(self) -> None:
        """Personas 26-35: Pen-testers trying SSRF, cloud metadata, directories, and CSV formula injection."""
        ssrf_targets = [
            "http://127.0.0.1:8000/admin",
            "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1/router",
            "http://10.0.0.1/internal",
            "ftp://malicious.example.com/file",
            "javascript:alert(1)",
        ]
        for url in ssrf_targets:
            with self.subTest(url=url):
                ok, _ = SSRFGuard.validate_url(url)
                self.assertFalse(ok, f"SSRFGuard failed to block {url}")

        # Directory blockers
        for bad_url in [
            "https://www.indiamart.com/company",
            "https://www.justdial.com/kolkata/x",
            "https://www.zaubacorp.com/company",
        ]:
            _, err = DomainDiscoveryAgent.canonicalize_domain(bad_url)
            self.assertIsNotNone(err)

        # CSV Formula Injection neutralization
        for payload in ["=cmd|' /C calc'!A0", "+SUM(1,1)", "-2+3", "@import"]:
            sanitized = safe_cell(payload)
            self.assertTrue(sanitized.startswith("'"), f"Formula injection not neutralized: {payload}")

    def test_personas_36_to_42_affluence_and_vehicle_valuation(self) -> None:
        """Personas 36-42: Luxury auto, commercial fleet, and HNI buyer qualification."""
        v1 = evaluate_vehicle_profile("Land Rover", "Defender 110", "")
        self.assertGreaterEqual(v1["estimated_inr"], 10_000_000)

        v2 = evaluate_vehicle_profile("BharatBenz", "12 Heavy Trucks Fleet", "")
        self.assertGreaterEqual(v2["estimated_inr"], 3_000_000)

        v3 = evaluate_vehicle_profile("", "", "")
        self.assertEqual(v3["estimated_inr"], 0)

        # Pan-India custom client onboarding (Pune / Maharashtra)
        pune_client = {
            "id": "pune_industrial",
            "target_states": ["maharashtra"],
            "sector_keywords": ["automotive", "manufacturing", "robotics"],
        }
        lead_res = qualify_and_score_lead(
            {
                "name": "Siddharth Deshmukh",
                "company": "Deccan Autocomp Pvt Ltd",
                "sector": "Automotive Manufacturing",
                "job_title": "Founder & CEO",
                "state": "Maharashtra",
                "city": "Pune",
                "annual_turnover": "₹64Cr",
                "vehicle_model": "Porsche Cayenne + BMW X7",
            },
            pune_client,
        )
        self.assertEqual(lead_res["lead_class"], "Q1")
        self.assertGreaterEqual(lead_res["composite_score"], 85)

    def test_personas_43_to_50_nontechnical_prompts_and_vault_idempotency(self) -> None:
        """Personas 43-50: Non-technical users typing vague/Hinglish prompts, empty strings, and rapid double-saves."""
        for prompt in [
            "",
            "   ",
            "howrah ke factory owners",
            "give me rich people with big cars and good business",
            "all companies",
        ]:
            filters = generate_multichoice_company_filters(prompt)
            self.assertTrue(any(c["selected"] for c in filters["company_sector_choices"]))
            self.assertTrue(any(c["selected"] for c in filters["company_turnover_choices"]))

        with tempfile.TemporaryDirectory() as d:
            vault = ProductionLeadVault(pathlib.Path(d) / "vault.sqlite")
            converted = [convert_crawler_record_to_v4_v5_row(r) for r in PILOT_RECORDS[:10]]
            # Double upsert must be idempotent (no duplicate primary key crash)
            vault.upsert_leads(converted, client_id="lakhotia")
            vault.upsert_leads(converted, client_id="lakhotia")
            stored = vault.list_leads(client_id="lakhotia")
            self.assertEqual(len(stored), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
