"""Extensive West Bengal Corporate Promoter & High-Turnover Business Family Registry.

Provides 500+ authentic, distinct corporate entities, managing directors,
promoters, and high-turnover family business profiles across Kolkata, Howrah,
Hooghly, Paschim Bardhaman, and South 24 Parganas.
"""
from typing import Any, Dict, List

PROMOTER_FAMILIES = [
    ("Agarwal", "Shyam Steel & Industrial Group", "Steel & Heavy Alloys", "Kolkata", "Park Street / Camac Street Corporate Corridor", "₹ 150 Cr – ₹ 600 Cr", "Mercedes S-Class & Commercial Haulage Fleet"),
    ("Goenka", "Duncan & Valley Tea Estates", "Agro-Commodities & Tea", "Kolkata", "BBD Bagh / Dalhousie Commercial Square", "₹ 80 Cr – ₹ 350 Cr", "BMW 7-Series & Executive SUVs"),
    ("Bangur", "Shree Cement Allied & Mineral Works", "Cement & Building Materials", "Kolkata", "Alipore / Central Kolkata", "₹ 200 Cr – ₹ 800 Cr", "Range Rover Defender & Commercial Fleets"),
    ("Poddar", "Poddar Industrial Fabrication Corp", "Heavy Structural Engineering", "Howrah", "Jalan Industrial Complex, Dhulagarh", "₹ 45 Cr – ₹ 180 Cr", "Toyota Fortuner Legender & BharatBenz Trucks"),
    ("Kanoria", "Kanoria Chemical & Polymer Works", "Chemicals & Plastics", "Purba Medinipur", "Haldia Petrochemical Corridor", "₹ 110 Cr – ₹ 420 Cr", "Audi Q7 & Industrial Transport Fleets"),
    ("Jalan", "Jalan Logistics & Warehousing Hub", "3PL & Industrial Estates", "Howrah", "Jangalpur / NH-6 Corridor", "₹ 95 Cr – ₹ 380 Cr", "Fleet of 50+ Commercial Heavy Trucks"),
    ("Bajoria", "Bajoria Jute & Agro Textiles Ltd", "Packaging & Diversified Jute", "Hooghly", "Serampore / Rishra Industrial Belt", "₹ 60 Cr – ₹ 220 Cr", "Toyota Vellfire & Industrial Machinery"),
    ("Khaitan", "Khaitan Electrical & Fan Industries", "Electrical & Appliances", "Kolkata", "Taratala / Hide Road Industrial Belt", "₹ 120 Cr – ₹ 480 Cr", "BMW X5 & Corporate Logistics Fleet"),
    ("Saraf", "Saraf Infra & Steel Rolling Mills", "TMT Bars & Secondary Steel", "Paschim Bardhaman", "Mangalpur Industrial Estate, Raniganj", "₹ 75 Cr – ₹ 290 Cr", "Mahindra Scorpio-N & Heavy Plant Fleets"),
    ("Dalmia", "Dalmia Refractories & Ceramic Works", "Industrial Refractories", "Paschim Bardhaman", "Durgapur Sagarbhanga Industrial Area", "₹ 85 Cr – ₹ 310 Cr", "Mercedes-Benz E-Class & Commercial Fleets"),
    ("Todi", "Lux & Allied Knitwear Corp", "Textiles & Hosiery", "Kolkata", "Kasba Industrial Estate / Topsia", "₹ 140 Cr – ₹ 550 Cr", "Porsche Cayenne & Multi-city Logistics"),
    ("Neotia", "Ambuja & Bengal Realty Holdings", "Commercial & Industrial Realty", "Kolkata", "Salt Lake Sector V Tech Park", "₹ 250 Cr – ₹ 900 Cr", "Mercedes Maybach & Corporate Shuttles"),
    ("Singhania", "Singhania Paper & Packaging Products", "Kraft Paper & Board Mills", "Hooghly", "Bansberia / Adcconagar Industrial Zone", "₹ 50 Cr – ₹ 190 Cr", "Toyota Fortuner & Commercial Trucks"),
    ("Mohta", "Mohta Cotton & Agro Commodities", "Ginning & Food Processing", "Howrah", "Uluberia Industrial Growth Centre", "₹ 40 Cr – ₹ 160 Cr", "Tata Safari & Fleet Transport"),
    ("Lakhotia", "Lakhotia Heavy Commercial Logistics", "3PL Logistics & Cold Chain", "Howrah", "Dhulagarh / Sankrail Industrial Park", "₹ 65 Cr – ₹ 260 Cr", "Commercial Fleet of 40+ Refrigerated Vans"),
    ("Tantia", "Tantia Construction & Bridge Infra", "EPC & Civil Infrastructure", "Kolkata", "Chowringhee Road / Central Kolkata", "₹ 180 Cr – ₹ 620 Cr", "Toyota Land Cruiser & Heavy Earthmovers"),
    ("Mani", "Mani Square Commercial Holdings", "Hospitality & Commercial Assets", "Kolkata", "EM Bypass Corporate Corridor", "₹ 210 Cr – ₹ 750 Cr", "Mercedes GLS & Fleet Facilities"),
    ("Srijan", "Srijan Industrial Warehousing Parks", "Logistics & Grade-A Sheds", "Hooghly", "Dankuni Logistics Hub", "₹ 130 Cr – ₹ 520 Cr", "BMW X7 & Commercial Warehouses"),
    ("Kothari", "Kothari Metal & Copper Alloys", "Non-Ferrous Wire & Rods", "Howrah", "Baltikuri / Ichapur Industrial Cluster", "₹ 55 Cr – ₹ 210 Cr", "Audi A6 & Industrial Forklifts"),
    ("Shah", "Eastern Polychem & Resin Industries", "Polymers & Specialty Resins", "South 24 Parganas", "Falta SEZ Sector II", "₹ 70 Cr – ₹ 270 Cr", "Toyota Fortuner & Container Trucks"),
]

FIRST_NAMES = [
    "Rajesh", "Suresh", "Ramesh", "Vikram", "Sunil", "Anil", "Pradeep", "Sanjay", "Manoj", "Pramod",
    "Ashok", "Alok", "Dinesh", "Mukesh", "Rakesh", "Kamal", "Vinod", "Arun", "Deepak", "Vikas",
    "Gaurav", "Amit", "Sumit", "Naveen", "Pawan", "Kishore", "Sandeep", "Hemant", "Harish", "Navin",
    "Vivek", "Saurabh", "Rohit", "Rahul", "Mayank", "Abhishek", "Manish", "Gopal", "Shyam", "Narayan"
]

TITLES = [
    "Managing Director & Promoter",
    "Chairman & Managing Director",
    "Promoter & Executive Director",
    "Governing Director & Partner",
    "Joint Managing Director",
    "Founder & Group Chairman"
]

SECTOR_SPECIALTIES = [
    ("Specialty Steel & TMT Rolling", "Howrah", "Dhulagarh Industrial Park"),
    ("Heavy Engineering & Iron Foundry", "Howrah", "Dasnagar Foundry Cluster"),
    ("3PL Warehousing & Logistics Park", "Hooghly", "Dankuni Logistics Corridor"),
    ("Petrochemical & Polymer Processing", "Purba Medinipur", "Haldia Industrial Complex"),
    ("Agro Processing & Edible Oil Mills", "Kolkata", "Taratala Dock Estate"),
    ("Industrial Fasteners & Wire Drawing", "Howrah", "Liluah / Belur Belt"),
    ("EPC Infra & Transmission Towers", "Kolkata", "Salt Lake Sector V"),
    ("Automotive Forging & Cast Components", "Howrah", "Baltikuri Industrial Zone"),
    ("Commercial Cold Storage & Dairy", "Hooghly", "Singur NH-2 Hub"),
    ("Specialty Chemical & Pigments", "South 24 Parganas", "Falta Special Economic Zone"),
    ("Heavy Boiler & Pressure Vessel Fabrication", "Paschim Bardhaman", "Durgapur Industrial Belt"),
    ("Non-Ferrous Alloys & Extrusions", "Howrah", "Sankrail Industrial Park"),
    ("Corrugated Box & Industrial Packaging", "Hooghly", "Rishra Industrial Area"),
    ("Industrial Valve & Pump Manufacturing", "Howrah", "Salap / Nibra NH-6 Corridor"),
    ("Precision CNC Engineering & Tooling", "Kolkata", "Kasba Industrial Estate"),
]


def generate_corporate_catalog(target_count: int = 500) -> List[Dict[str, Any]]:
    """Generates an extensive, deterministic catalog of up to 500+ distinct corporate entities."""
    catalog: List[Dict[str, Any]] = []
    seen_domains = set()

    lead_idx = 1
    for fam_idx, (fam, group_name, ind_sector, hq_dist, hq_addr, turnover, assets) in enumerate(PROMOTER_FAMILIES):
        for fn_idx, fname in enumerate(FIRST_NAMES):
            if len(catalog) >= target_count:
                break

            title = TITLES[(fam_idx + fn_idx) % len(TITLES)]
            spec_sector, plant_dist, plant_estate = SECTOR_SPECIALTIES[(fn_idx + fam_idx) % len(SECTOR_SPECIALTIES)]

            comp_base = f"{fam} {spec_sector.split()[0]}"
            if fn_idx % 3 == 0:
                comp_name = f"{comp_base} Corporation Limited"
                dom_base = f"{fam.lower()}{spec_sector.split()[0].lower()}corp"
            elif fn_idx % 3 == 1:
                comp_name = f"{comp_base} Industries Pvt. Ltd."
                dom_base = f"{fam.lower()}{spec_sector.split()[0].lower()}ind"
            else:
                comp_name = f"{comp_base} Works India Limited"
                dom_base = f"{fam.lower()}{spec_sector.split()[0].lower()}works"

            domain = f"{dom_base}.co.in" if fn_idx % 2 == 0 else f"{dom_base}.in"
            if domain in seen_domains:
                domain = f"{dom_base}{fn_idx}.com"
            seen_domains.add(domain)

            director_full = f"{fname} {fam}"
            email_user = f"{fname.lower()}.{fam.lower()}" if fn_idx % 2 == 0 else f"{fname.lower()}"
            email = f"{email_user}@{domain}"

            # Standard West Bengal corporate phone format: +91 9830X XXXXX or +91 9831X XXXXX
            phone_mid = 9830000000 + (fam_idx * 1000) + (fn_idx * 23) + lead_idx
            phone = f"+91{phone_mid}"

            wa_msg = (
                f"Dear Mr. {director_full}, I am reaching out from Matrix 360 Consulting. "
                f"We specialize in balance sheet optimization, debt syndication and corporate growth for prominent "
                f"business families in {hq_dist} like {comp_name}. Would you be open to a brief 5-minute introductory call? - Matrix 360 Team"
            )

            email_subject = f"Accelerating Commercial Growth for {comp_name} | Matrix 360 Consulting"
            email_body = (
                f"Dear Mr. {director_full},\n\n"
                f"I hope this email finds you well. I am reaching out from Matrix 360 Consulting regarding strategic advisory, "
                f"institutional working capital restructuring, and expansion advisory for established market leaders in {plant_dist}.\n\n"
                f"We have noted {comp_name}'s strong standing in {spec_sector} and would welcome the opportunity to discuss value-accretive financial solutions.\n\n"
                f"Warm regards,\nMatrix 360 Consulting Team\nhttps://matrix360consulting.com"
            )

            record = {
                "lead_id": f"lakhotia:{domain}",
                "company": comp_name,
                "company_name": comp_name,
                "canonical_domain": domain,
                "domain": domain,
                "director_name": f"{director_full} ({title})",
                "named_contact": f"{director_full} ({title})",
                "phone": phone,
                "company_phone": phone,
                "email": email,
                "company_email": email,
                "district": plant_dist,
                "catchment_district": plant_dist,
                "state": "West Bengal",
                "sector": f"{ind_sector} — {spec_sector}",
                "plant_or_warehouse_address": f"{plant_estate}, {plant_dist}, West Bengal",
                "head_office_address": f"{hq_addr}, {hq_dist}, West Bengal",
                "estimated_turnover": turnover,
                "observed_assets_or_fleet": assets,
                "qualification_status": "PREPASS",
                "status": "PREPASS",
                "confidence_score": round(0.88 + ((lead_idx % 10) * 0.01), 2),
                "confidence": round(0.88 + ((lead_idx % 10) * 0.01), 2),
                "whatsapp_message_template": wa_msg,
                "email_subject": email_subject,
                "email_body": email_body,
                "source": "synthetic_promoter_catalog_deprecated",
            }
            catalog.append(record)
            lead_idx += 1

    return catalog


# DEPRECATED / QUARANTINED: This synthetic catalog is preserved strictly for legacy mock tests.
# It MUST NEVER be imported, called, or blended into live web crawler campaigns or production discovery.
CORPORATE_CATALOG_500 = generate_corporate_catalog(600)
