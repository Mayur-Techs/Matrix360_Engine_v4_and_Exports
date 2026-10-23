import sys
from pathlib import Path
_pkg_root = Path(__file__).resolve().parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
import unittest
from agents import (
    PromptFilterAgent,
    DomainDiscoveryAgent,
    QualificationAgent,
    ContactExtractionAgent,
)
from discovery_zero_api import (
    ObfuscatedContactDecoder,
    CrtShHarvester,
    OverpassIndustrialHarvester,
    SupplyChainSnowballSpider,
    KeylessSearchRotator,
    ArchivalIndexHarvester,
    HybridScaleOrchestrator,
)
from verified_pilot_data import PILOT_RECORDS


class TestLeadDiscoveryEngine(unittest.TestCase):
    def test_01_prompt_filter_agent_client_agnostic(self):
        agent = PromptFilterAgent()
        wb_spec = agent.generate_filters(
            "Find manufacturing factories, engineering works, and 3PL warehouses near Howrah, Kolkata, and Hooghly",
            lead_count=500
        )
        self.assertEqual(wb_spec.target_lead_count, 500)
        self.assertTrue(any("Howrah" in c for c in wb_spec.catchment_locations))
        self.assertTrue(len(wb_spec.positive_signals) >= 3)
        self.assertTrue(len(wb_spec.negative_exclusions) >= 3)

        custom_spec = agent.generate_filters(
            "Find cold chain pharmaceutical distributors and medical device manufacturers in Pune and Mumbai",
            lead_count=250
        )
        self.assertEqual(custom_spec.target_lead_count, 250)
        self.assertIn("Pune", custom_spec.prompt_summary)

    def test_02_domain_canonicalization_and_ssrf_guard(self):
        dom, reason = DomainDiscoveryAgent.canonicalize_domain("https://www.glosterjute.com/contact-us")
        self.assertEqual(dom, "glosterjute.com")
        self.assertIsNone(reason)

        dom2, reason2 = DomainDiscoveryAgent.canonicalize_domain("https://www.indiamart.com/lakshmi-foundry-works/aboutus.html")
        self.assertIsNotNone(reason2)
        self.assertIn("THIRD_PARTY_DIRECTORY", reason2)

        dom3, reason3 = DomainDiscoveryAgent.canonicalize_domain("http://192.168.1.15/admin")
        self.assertEqual(reason3, "PRIVATE_OR_RESERVED_IP_TARGET")

        dom4, reason4 = DomainDiscoveryAgent.canonicalize_domain("http://127.0.0.1:8080/")
        self.assertEqual(reason4, "PRIVATE_OR_RESERVED_IP_TARGET")

    def test_03_qualification_agent_prepass_review_exclude(self):
        q = QualificationAgent()
        status, reasons, conf = q.evaluate(
            domain="ganeshconsumer.com",
            company_name="Ganesh Consumer Products Limited",
            sector="Food Processing & Agro Manufacturing",
            facility_evidence="Manufacturing Plant at Jalan Industrial Complex, Howrah-711411",
            location_type="Plant / Factory + Head Office",
            address_text="Jalan Industrial Complex, Howrah - 711411"
        )
        self.assertEqual(status, "PREPASS")
        self.assertGreaterEqual(conf, 0.90)

        status_ex, reasons_ex, _ = q.evaluate(
            domain="mbaazar.in",
            company_name="M Baazar – The Fashion Store",
            sector="Retail Fashion Store",
            facility_evidence="Menswear and Ladieswear outlets",
            location_type="Retail Store (Excluded)",
            address_text="Andul Road, Howrah"
        )
        self.assertEqual(status_ex, "EXCLUDE")

    def test_04_contact_extraction_and_link_prioritization(self):
        sample = "Reach us at info[at]balmerlawrie[dot]com or sales@ganeshconsumer.com or call +91 9830173124 and 033-2225-4489."
        res = ContactExtractionAgent.extract_from_text(sample)
        self.assertIn("info@balmerlawrie.com", res["emails"])
        self.assertIn("sales@ganeshconsumer.com", res["emails"])
        self.assertTrue(len(res["phones"]) >= 2)

        links = [
            "https://example.com/blog/post-1",
            "https://example.com/contact-us",
            "https://example.com/our-facilities",
            "https://external.com/contact"
        ]
        prioritized = ContactExtractionAgent.prioritize_in_domain_links("example.com", links)
        self.assertEqual(len(prioritized), 3)
        self.assertIn("https://example.com/contact-us", prioritized[:2])

    def test_05_pilot_dataset_integrity_and_distinct_fields(self):
        prepass = [r for r in PILOT_RECORDS if r["qualification_status"] == "PREPASS"]
        review = [r for r in PILOT_RECORDS if r["qualification_status"] == "REVIEW"]
        exclude = [r for r in PILOT_RECORDS if r["qualification_status"] == "EXCLUDE"]
        self.assertGreaterEqual(len(prepass) + len(review), 50)
        self.assertGreaterEqual(len(exclude), 8)

        eligible_domains = [r["canonical_domain"] for r in prepass + review]
        self.assertEqual(len(eligible_domains), len(set(eligible_domains)))

        required_cols = {
            "company_phone", "company_email", "named_contact",
            "role", "contact_person_email", "contact_person_phone",
            "location_type", "plant_or_warehouse_address", "head_office_address"
        }
        for r in PILOT_RECORDS:
            self.assertTrue(required_cols.issubset(set(r.keys())))
            if not r["named_contact"]:
                self.assertEqual(r["contact_person_email"], "")

    def test_06_cloudflare_cfemail_xor_decoder_and_regulatory_ids(self):
        # Encode "sales@howrahfoundry.co.in" with XOR key 0x5A (90)
        target_email = "sales@howrahfoundry.co.in"
        key = 0x5A
        hex_payload = f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in target_email)

        decoded = ObfuscatedContactDecoder.decode_cfemail(hex_payload)
        self.assertEqual(decoded, target_email)

        raw_html = f"""
        <html><body>
          <a class="__cf_email__" data-cfemail="{hex_payload}">[email&#160;protected]</a>
          <script>var e = 'export' + '@' + 'sankrailsteel.com';</script>
          <p>GSTIN: 19AABCP5269J1ZZ | CIN: L17100WB1923PLC004628 | MSME: UDYAM-WB-10-0012345</p>
        </body></html>
        """
        bundle = ObfuscatedContactDecoder.extract_all_from_html(raw_html)
        self.assertIn("sales@howrahfoundry.co.in", bundle["emails"])
        self.assertIn("export@sankrailsteel.com", bundle["emails"])
        self.assertIn("19AABCP5269J1ZZ", bundle["wb_gstins"])
        self.assertIn("L17100WB1923PLC004628", bundle["wb_cins"])
        self.assertIn("UDYAM-WB-10-0012345", bundle["udyam_ids"])

    def test_07_zero_api_multi_vector_discovery_500_to_5000(self):
        # Test Keyless Dork Matrix generation for 5,000 leads without Serper API
        plan_5000 = HybridScaleOrchestrator.build_scale_plan(
            "Find manufacturers and 3PL warehouses in Howrah, Hooghly, and Kolkata",
            target_leads=5000
        )
        self.assertEqual(plan_5000.target_leads, 5000)
        self.assertGreaterEqual(plan_5000.total_dorks_generated, 600)
        self.assertEqual(len(plan_5000.active_vectors), 8)
        self.assertIn("landuse", plan_5000.overpass_ql_query)

        # Test crt.sh JSON parser
        mock_crt_json = '[{"common_name": "*.uluberiasteels.co.in", "name_value": "uluberiasteels.co.in\\nwww.dankunilogistics.in"}]'
        crt_domains = CrtShHarvester.parse_crt_json(mock_crt_json)
        self.assertIn("uluberiasteels.co.in", crt_domains)
        self.assertIn("dankunilogistics.in", crt_domains)

        # Test OpenStreetMap Overpass parser
        mock_osm_json = '{"elements": [{"tags": {"name": "Sankrail Polymer Works", "website": "https://www.sankrailpolymers.in", "addr:postcode": "711302"}}]}'
        osm_leads = OverpassIndustrialHarvester.parse_overpass_response(mock_osm_json)
        self.assertEqual(len(osm_leads), 1)
        self.assertEqual(osm_leads[0]["canonical_domain"], "sankrailpolymers.in")

        # Test DuckDuckGo HTML / Bing HTML parser with directory rejection
        mock_ddg_html = """
        <div>
          <a href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.baidyabatiforgings.com%2Fcontact-us">Baidyabati Forgings</a>
          <a href="https://www.indiamart.com/some-directory">IndiaMart Directory</a>
        </div>
        """
        parsed_search = KeylessSearchRotator.parse_search_html_for_domains(mock_ddg_html)
        self.assertEqual(len(parsed_search), 1)
        self.assertEqual(parsed_search[0]["canonical_domain"], "baidyabatiforgings.com")

        # Test Supply-Chain Snowball Spider + Sitemap XML parser
        partner_html = '<a href="https://www.ancillaryvalveshowrah.com">Vendor</a><a href="https://www.justdial.com/x">JD</a>'
        snowballed = SupplyChainSnowballSpider.extract_outbound_company_domains(partner_html, "mainplant.com")
        self.assertEqual(snowballed, ["ancillaryvalveshowrah.com"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
