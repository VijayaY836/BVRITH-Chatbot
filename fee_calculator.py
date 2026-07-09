"""
fee_calculator.py — BVRIT Hyderabad Fee Calculator Tool

Computes total fees across years, hostel + tuition combinations,
and scholarship/concession estimates for BVRITH programmes.

Usage (standalone):
    python fee_calculator.py

Usage (as module):
    from fee_calculator import calculate_fees
    result = calculate_fees(branch="CSE", batch_year=2025, years=4, hostel=True)
"""

from __future__ import annotations

# ── Fee tables (per academic year, in INR) ────────────────────────────────────
# Source: BVRIT Hyderabad Fee Details page, captured July 2026
# Format: { batch_year: { branch: { component: amount } } }

FEE_TABLE: dict[int, dict[str, dict[str, int]]] = {
    2025: {
        "CSE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "ECE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "EEE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "CSM":     {"tuition": 120000, "nba": 0,    "jntuh_misc": 5500},
        "CSE-AIML":{"tuition": 120000, "nba": 0,    "jntuh_misc": 5500},
    },
    2024: {
        "CSE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "ECE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "EEE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "CSM":     {"tuition": 120000, "nba": 0,    "jntuh_misc": 5500},
        "CSE-AIML":{"tuition": 120000, "nba": 0,    "jntuh_misc": 5500},
    },
    2023: {
        "CSE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "ECE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "EEE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "IT":      {"tuition": 120000, "nba": 3000, "jntuh_misc": 5500},
        "CSM":     {"tuition": 120000, "nba": 0,    "jntuh_misc": 5500},
        "CSE-AIML":{"tuition": 120000, "nba": 0,    "jntuh_misc": 5500},
    },
    2022: {
        "CSE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 2500},
        "ECE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 2500},
        "EEE":     {"tuition": 120000, "nba": 3000, "jntuh_misc": 2500},
        "IT":      {"tuition": 120000, "nba": 3000, "jntuh_misc": 2500},
        "CSM":     {"tuition": 120000, "nba": 0,    "jntuh_misc": 2500},
        "CSE-AIML":{"tuition": 120000, "nba": 0,    "jntuh_misc": 2500},
    },
    2021: {
        "CSE":     {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "ECE":     {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "EEE":     {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "IT":      {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "CSM":     {"tuition": 90000, "nba": 0,    "jntuh_misc": 5500},
        "CSE-AIML":{"tuition": 90000, "nba": 0,    "jntuh_misc": 5500},
    },
    2020: {
        "CSE":     {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "ECE":     {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "EEE":     {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "IT":      {"tuition": 90000, "nba": 3000, "jntuh_misc": 5500},
        "CSM":     {"tuition": 90000, "nba": 0,    "jntuh_misc": 5500},
        "CSE-AIML":{"tuition": 90000, "nba": 0,    "jntuh_misc": 5500},
    },
}

# M.Tech programmes (2-year PG) — fee estimate based on available data
MTECH_FEE_TABLE: dict[str, dict[str, int]] = {
    "MTECH_DATA_SCIENCES": {"tuition": 75000, "jntuh_misc": 5500},
    "MTECH_VLSI":          {"tuition": 75000, "jntuh_misc": 5500},
    "MTECH_CSE":           {"tuition": 75000, "jntuh_misc": 5500},
}

# Hostel fee estimate (approximate; contact admissions for exact figures)
HOSTEL_FEE_PER_YEAR = 85000   # includes room + mess (approximate)
TRANSPORT_FEE_PER_YEAR = 25000  # approximate for day scholars using college bus

# Known scholarship / concession schemes
SCHOLARSHIPS = {
    "TS ePass":         {"type": "govt", "covers": "full tuition for eligible SC/ST/BC students"},
    "PM Vidyalaxmi":    {"type": "central_govt", "covers": "education loan at subsidised rate"},
    "Merit scholarship":{"type": "college", "covers": "partial tuition waiver for top rankers"},
    "NV Lakshmi Foundation": {"type": "trust", "covers": "financial aid for deserving students"},
}

# Branch name aliases for user-friendly input
BRANCH_ALIASES: dict[str, str] = {
    "cse": "CSE",
    "computer science": "CSE",
    "computer science engineering": "CSE",
    "ece": "ECE",
    "electronics": "ECE",
    "electronics and communication": "ECE",
    "eee": "EEE",
    "electrical": "EEE",
    "electrical and electronics": "EEE",
    "it": "IT",
    "information technology": "IT",
    "csm": "CSM",
    "cse aiml": "CSM",
    "cse-aiml": "CSM",
    "cse ai&ml": "CSM",
    "ai ml": "CSM",
    "artificial intelligence": "CSM",
    # M.Tech — use internal keys to avoid collision with UG CSE
    "data sciences": "MTECH_DATA_SCIENCES",
    "data science": "MTECH_DATA_SCIENCES",
    "mtech data sciences": "MTECH_DATA_SCIENCES",
    "vlsi": "MTECH_VLSI",
    "vlsi design": "MTECH_VLSI",
    "mtech vlsi": "MTECH_VLSI",
    "mtech cse": "MTECH_CSE",
    "m.tech cse": "MTECH_CSE",
    "mtech computer science": "MTECH_CSE",
}


def normalise_branch(branch: str) -> str:
    return BRANCH_ALIASES.get(branch.lower().strip(), branch.upper().strip())


def calculate_fees(
    branch: str,
    batch_year: int,
    years: int | None = None,
    hostel: bool = False,
    transport: bool = False,
    scholarship: str | None = None,
    scholarship_pct: float = 0.0,
) -> dict:
    """
    Calculate total BVRIT Hyderabad fees for a given branch and batch.

    Args:
        branch:          Branch name (CSE / ECE / EEE / CSM / IT / MTECH_CSE / etc.)
        batch_year:      Year of admission (2020–2025 for UG)
        years:           Number of years (default: 4 for B.Tech, 2 for M.Tech)
        hostel:          Include hostel + mess fee estimate
        transport:       Include college bus fee estimate
        scholarship:     Scholarship name (optional, for display)
        scholarship_pct: Percentage discount on tuition fee (0–100)

    Returns:
        dict with per-year breakdown and totals
    """
    branch = normalise_branch(branch)

    # Validate scholarship percentage
    if scholarship_pct < 0 or scholarship_pct > 100:
        return {
            "error": f"Invalid scholarship percentage: {scholarship_pct}%. Scholarships must be between 0% and 100%.",
            "note": "A scholarship cannot exceed 100% of the tuition fee. Please enter a valid percentage.",
        }

    # Check M.Tech
    is_mtech = branch in MTECH_FEE_TABLE
    if is_mtech:
        fee_data = MTECH_FEE_TABLE[branch]
        duration = years or 2
        display_branch = {"MTECH_DATA_SCIENCES": "Data Sciences", "MTECH_VLSI": "VLSI Design", "MTECH_CSE": "CSE"}.get(branch, branch)
    else:
        if batch_year not in FEE_TABLE:
            available = sorted(FEE_TABLE.keys())
            return {
                "error": f"Batch year {batch_year} not in fee table. Available years: {available}",
                "note": "Contact admissions for fee details of other years.",
            }
        year_data = FEE_TABLE[batch_year]
        if branch not in year_data:
            available = list(year_data.keys())
            return {
                "error": f"Branch '{branch}' not found for batch {batch_year}. Available: {available}",
            }
        fee_data = year_data[branch]
        duration = years or 4
        display_branch = branch

    # Apply scholarship discount to tuition only
    base_tuition = fee_data.get("tuition", 0)
    discount = round(base_tuition * scholarship_pct / 100)
    discounted_tuition = base_tuition - discount
    nba_per_year = fee_data.get("nba", 0)

    # Build per-year breakdown
    yearly = []
    for y in range(1, duration + 1):
        row = {
            "year": y,
            "tuition": base_tuition,
            "discount": discount,
            "tuition_after_discount": discounted_tuition,
            "nba_fee": nba_per_year,
            "jntuh_misc": fee_data.get("jntuh_misc", 0),
            "hostel": HOSTEL_FEE_PER_YEAR if hostel else 0,
            "transport": TRANSPORT_FEE_PER_YEAR if transport else 0,
        }
        row["year_total"] = (
            discounted_tuition + row["nba_fee"] + row["jntuh_misc"]
            + row["hostel"] + row["transport"]
        )
        yearly.append(row)

    academic_total = sum(r["tuition_after_discount"] + r["nba_fee"] + r["jntuh_misc"] for r in yearly)
    total_discount = discount * duration
    hostel_total = HOSTEL_FEE_PER_YEAR * duration if hostel else 0
    transport_total = TRANSPORT_FEE_PER_YEAR * duration if transport else 0
    grand_total = academic_total + hostel_total + transport_total

    # Scholarship info
    scholarship_info = None
    if scholarship or scholarship_pct > 0:
        scholarship_info = {
            "name": scholarship or f"{scholarship_pct}% tuition discount",
            "pct": scholarship_pct,
            "discount_per_year": discount,
            "total_discount": total_discount,
        }
        if scholarship:
            key = scholarship.lower().strip()
            known = next((v for k, v in SCHOLARSHIPS.items() if key in k.lower()), None)
            if known:
                scholarship_info.update(known)

    return {
        "branch": display_branch,
        "batch_year": batch_year,
        "programme": "M.Tech" if is_mtech else "B.Tech",
        "duration_years": duration,
        "per_year_breakdown": yearly,
        "scholarship_pct": scholarship_pct,
        "total_discount": total_discount,
        "academic_total": academic_total,
        "hostel_total": hostel_total,
        "transport_total": transport_total,
        "grand_total": grand_total,
        "scholarship": scholarship_info,
        "disclaimer": (
            "Fees are based on officially published figures and are subject to revision "
            "by the college or TSCHE. Hostel and transport figures are estimates. "
            "Always confirm with the BVRITH admissions office before making financial decisions. "
            "Contact: Dr J. Manoj Kumar — 92471 64714."
        ),
    }


def format_fee_response(result: dict) -> str:
    """Format calculate_fees() result as a human-readable markdown string."""
    if "error" in result:
        return f"❌ {result['error']}\n\n_{result.get('note', '')}_"

    has_discount = result.get("scholarship_pct", 0) > 0

    lines = [
        f"## Fee Estimate — {result['branch']} ({result['programme']}, {result['batch_year']} batch)",
        f"**Duration:** {result['duration_years']} years\n",
    ]

    if has_discount:
        lines += [
            f"| Year | Tuition | Discount ({result['scholarship_pct']}%) | After Discount | NBA Fee | JNTUH/Misc | Hostel | Transport | **Year Total** |",
            "|------|---------|---------|----------------|---------|------------|--------|-----------|---------------|",
        ]
        for r in result["per_year_breakdown"]:
            lines.append(
                f"| Year {r['year']} "
                f"| ₹{r['tuition']:,} "
                f"| -₹{r['discount']:,} "
                f"| ₹{r['tuition_after_discount']:,} "
                f"| ₹{r['nba_fee']:,} "
                f"| ₹{r['jntuh_misc']:,} "
                f"| ₹{r['hostel']:,} "
                f"| ₹{r['transport']:,} "
                f"| **₹{r['year_total']:,}** |"
            )
    else:
        lines += [
            "| Year | Tuition | NBA Fee | JNTUH/Misc | Hostel | Transport | **Year Total** |",
            "|------|---------|---------|------------|--------|-----------|---------------|",
        ]
        for r in result["per_year_breakdown"]:
            lines.append(
                f"| Year {r['year']} "
                f"| ₹{r['tuition']:,} "
                f"| ₹{r['nba_fee']:,} "
                f"| ₹{r['jntuh_misc']:,} "
                f"| ₹{r['hostel']:,} "
                f"| ₹{r['transport']:,} "
                f"| **₹{r['year_total']:,}** |"
            )

    lines += ["", f"**Academic fees total ({result['duration_years']} yrs):** ₹{result['academic_total']:,}"]

    if has_discount:
        lines.append(f"**Total scholarship savings:** -₹{result['total_discount']:,}")

    if result["hostel_total"]:
        lines.append(f"**Hostel + mess total:** ₹{result['hostel_total']:,} _(estimate)_")
    if result["transport_total"]:
        lines.append(f"**Transport total:** ₹{result['transport_total']:,} _(estimate)_")
    lines.append(f"\n### 💰 Grand Total: ₹{result['grand_total']:,}")

    if result.get("scholarship"):
        s = result["scholarship"]
        if s.get("covers"):
            lines.append(f"\n**Scholarship — {s['name']}:** {s['covers']}")

    lines += ["", f"_{result['disclaimer']}_"]
    return "\n".join(lines)


def get_available_scholarships() -> str:
    """Return a formatted list of known BVRIT scholarships."""
    lines = ["**Known scholarship / financial aid schemes at BVRITH:**\n"]
    for name, info in SCHOLARSHIPS.items():
        lines.append(f"- **{name}** ({info['type']}): {info['covers']}")
    lines.append(
        "\n_Contact the admissions office for eligibility criteria and application process._"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick demo
    print("=== CSE 2025 Batch — 4 years, with hostel ===")
    result = calculate_fees("CSE", 2025, hostel=True)
    print(format_fee_response(result))

    print("\n=== EEE 2024 Batch — 4 years, day scholar ===")
    result = calculate_fees("EEE", 2024)
    print(format_fee_response(result))

    print("\n=== M.Tech Data Sciences ===")
    result = calculate_fees("Data Sciences", 2025)
    print(format_fee_response(result))

    print("\n=== Scholarships ===")
    print(get_available_scholarships())
