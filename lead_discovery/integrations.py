import sys
from pathlib import Path
_pkg_root = Path(__file__).resolve().parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
"""
External CRM, Sequencer & Signed Webhook Integrations (`integrations.py`)
"""
import json
import time
import urllib.request
from typing import Any, Dict, List

from security import SSRFGuard, WebhookSigner


class CRMIntegrationHub:
    SUPPORTED_SYSTEMS = [
        {
            "id": "hubspot",
            "name": "HubSpot CRM",
            "category": "CRM",
            "endpoint_pattern": "https://api.hubapi.com/crm/v3/objects/companies/batch/create",
            "auth_type": "Bearer Private App Token",
        },
        {
            "id": "salesforce",
            "name": "Salesforce Cloud",
            "category": "CRM",
            "endpoint_pattern": "https://{instance}.my.salesforce.com/services/data/v60.0/composite/tree/Account",
            "auth_type": "OAuth2 / Bearer Token",
        },
        {
            "id": "zoho",
            "name": "Zoho CRM",
            "category": "CRM",
            "endpoint_pattern": "https://www.zohoapis.in/crm/v6/Leads",
            "auth_type": "Zoho-oauthtoken",
        },
        {
            "id": "pipedrive",
            "name": "Pipedrive",
            "category": "CRM",
            "endpoint_pattern": "https://api.pipedrive.com/v1/organizations",
            "auth_type": "API Token",
        },
        {
            "id": "apollo_instantly",
            "name": "Instantly / Smartlead / Apollo",
            "category": "Outreach Sequencer",
            "endpoint_pattern": "https://api.instantly.ai/api/v1/lead/add",
            "auth_type": "Campaign API Key",
        },
        {
            "id": "webhook",
            "name": "Custom Webhook (Zapier / Make / n8n / Clay)",
            "category": "Automation & ERP",
            "endpoint_pattern": "https://hooks.zapier.com/... or https://hook.eu1.make.com/...",
            "auth_type": "HMAC-SHA256 Signed Header (X-Vanguard-Signature-256)",
        },
    ]

    @staticmethod
    def build_hubspot_batch_payload(leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        inputs = []
        for r in leads:
            inputs.append({
                "properties": {
                    "name": r.get("company_name", ""),
                    "domain": r.get("canonical_domain", ""),
                    "industry": r.get("sector", ""),
                    "phone": r.get("company_phone", ""),
                    "address": r.get("plant_or_warehouse_address", ""),
                    "city": r.get("catchment_district", ""),
                    "description": (
                        f"Status: {r.get('qualification_status')} | "
                        f"Location Type: {r.get('location_type')} | "
                        f"Facility Evidence: {r.get('facility_evidence')} | "
                        f"Company Email: {r.get('company_email')} | "
                        f"Decision Maker: {r.get('named_contact')} ({r.get('role')}) "
                        f"{r.get('contact_person_email')} {r.get('contact_person_phone')}"
                    ).strip(),
                }
            })
        return {"inputs": inputs}

    @staticmethod
    def build_salesforce_composite_payload(leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        records = []
        for idx, r in enumerate(leads):
            acct: Dict[str, Any] = {
                "attributes": {"type": "Account", "referenceId": f"ref_acct_{idx}"},
                "Name": r.get("company_name", ""),
                "Website": f"https://{r.get('canonical_domain', '')}",
                "Phone": r.get("company_phone", ""),
                "Industry": r.get("sector", "")[:40],
                "BillingStreet": r.get("plant_or_warehouse_address", ""),
                "ShippingStreet": r.get("head_office_address", ""),
                "Description": r.get("facility_evidence", ""),
            }
            if r.get("named_contact"):
                names = [n.strip() for n in r["named_contact"].split("|") if n.strip()]
                roles = [ro.strip() for ro in (r.get("role") or "").split("|")]
                p_emails = [pe.strip() for pe in (r.get("contact_person_email") or "").split("|") if pe.strip()]
                p_phones = [pp.strip() for pp in (r.get("contact_person_phone") or "").split("|") if pp.strip()]
                contact_nodes = []
                for c_idx, person_name in enumerate(names):
                    contact_nodes.append({
                        "attributes": {"type": "Contact", "referenceId": f"ref_cont_{idx}_{c_idx}"},
                        "LastName": person_name,
                        "Title": roles[c_idx] if c_idx < len(roles) else (roles[0] if roles else "Decision Maker"),
                        "Email": p_emails[c_idx] if c_idx < len(p_emails) else "",
                        "Phone": p_phones[c_idx] if c_idx < len(p_phones) else "",
                    })
                acct["Contacts"] = {"records": contact_nodes}
            records.append(acct)
        return {"records": records}

    @classmethod
    def build_signed_webhook_envelope(
        cls,
        leads: List[Dict[str, Any]],
        campaign_name: str,
        webhook_secret: str = "vanguard-prod-secret",
    ) -> Dict[str, Any]:
        body = {
            "event": "leads.qualified.batch",
            "timestamp": int(time.time()),
            "campaign": campaign_name,
            "count": len(leads),
            "records": leads,
        }
        raw_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
        sig = WebhookSigner.sign_payload(raw_bytes, webhook_secret)
        return {
            "headers": {
                "Content-Type": "application/json",
                "X-Vanguard-Signature-256": sig,
                "X-Vanguard-Event": "leads.qualified.batch",
            },
            "payload": body,
        }

    @classmethod
    def dispatch_webhook(
        cls,
        target_url: str,
        leads: List[Dict[str, Any]],
        campaign_name: str,
        webhook_secret: str = "vanguard-prod-secret",
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        is_safe, safety_reason = SSRFGuard.validate_url(target_url, resolve_dns=not dry_run)
        if not is_safe:
            return {
                "delivered": False,
                "blocked_by_ssrf_guard": True,
                "reason": safety_reason,
            }

        envelope = cls.build_signed_webhook_envelope(leads, campaign_name, webhook_secret)
        if dry_run:
            return {
                "delivered": True,
                "mode": "DRY_RUN_VERIFIED",
                "target_url": target_url,
                "records_prepared": len(leads),
                "signature_header": envelope["headers"]["X-Vanguard-Signature-256"],
            }

        try:
            data_bytes = json.dumps(envelope["payload"]).encode("utf-8")
            req = urllib.request.Request(
                target_url,
                data=data_bytes,
                headers=envelope["headers"],
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                return {
                    "delivered": 200 <= resp.status < 300,
                    "http_status": resp.status,
                    "records_sent": len(leads),
                    "signature_header": envelope["headers"]["X-Vanguard-Signature-256"],
                }
        except Exception as exc:
            return {
                "delivered": False,
                "error": f"{type(exc).__name__}: {str(exc)[:160]}",
            }
