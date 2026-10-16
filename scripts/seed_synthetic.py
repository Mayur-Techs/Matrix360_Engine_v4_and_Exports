"""Create a small, safe demo source; it contains no real customer data."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROWS = [
    ["Name", "Company", "Sector", "City", "State", "Email", "Phone"],
    ["Demo Industrial", "North Steel Works", "manufacturing", "Howrah", "West Bengal", "industrial@example.invalid", "9876543210"],
    ["Demo Residence", "", "", "Chandannagar", "West Bengal", "shree@example.invalid", "9876543211"],
    ["Demo Community", "", "", "Kalyani", "West Bengal", "vrindavan@example.invalid", "9876543212"],
    ["Outside Review", "Pune Engineering", "engineering", "Pune", "Maharashtra", "outside@example.invalid", "9876543213"],
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="demo/matrix360_synthetic.csv")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(ROWS)
    print(output.resolve())

