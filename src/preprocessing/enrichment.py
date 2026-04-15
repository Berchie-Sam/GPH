"""
Hansard Enrichment Pipeline

Match parsed Hansard speaker turns to MP reference data and fill in
missing fields (party, constituency, region, etc.).
"""

import csv
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict, Counter
import difflib


def _normalise_name(name: str) -> str:
    """Canonical name key for matching."""
    import re
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"-", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.lower()


def _load_csv(path: str) -> List[Dict]:
    """Load CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def enrich_hansard(
    hansard_path: str,
    ref_path: str,
    output_path: str = None,
) -> Tuple[List[Dict], Dict, str]:
    """
    Match Hansard speakers to MP reference and fill missing fields.

    Matching strategy (in priority order):
    1. Exact normalised name match
    2. Constituency match (if speaker already has constituency)
    3. Token-set match (reversed names: "Mahama Ayariga" = "Ayariga Mahama")
    4. Fuzzy name match (score ≥ 0.75)

    New columns added:
      mp_id, region, majority, previous_mp, previous_party,
      match_score, match_method

    Returns:
        (enriched_rows, report_dict, output_path)
    """
    hansard_rows = _load_csv(hansard_path)
    ref_rows = _load_csv(ref_path)

    # Index reference data
    ref_by_name = {r["name_normalised"]: r for r in ref_rows}
    ref_by_const = {
        r["constituency"].lower().strip(): r
        for r in ref_rows if r.get("constituency")
    }
    ref_names = list(ref_by_name.keys())

    NEW_COLS = [
        "mp_id", "region", "majority", "previous_mp",
        "previous_party", "match_score", "match_method"
    ]

    enriched = []
    report = {
        "total_rows": len(hansard_rows),
        "stage_rows": 0,
        "speaker_rows": 0,
        "matched": 0,
        "unmatched": [],
        "methods": defaultdict(int),
        "fields_filled": {c: 0 for c in ["party", "constituency", "mp_id", "region"]},
    }

    # Known non-MP roles
    NON_MP_ROLES = {
        "first deputy speaker", "second deputy speaker", "speaker",
        "the speaker", "deputy speaker", "clerk", "mr speaker",
        "madam speaker", "the clerk", "deputy clerk",
    }

    for r in hansard_rows:
        row = dict(r)
        for col in NEW_COLS:
            row.setdefault(col, "")

        # Skip stage directions
        if row.get("is_stage_direction") == "1":
            report["stage_rows"] += 1
            enriched.append(row)
            continue

        report["speaker_rows"] += 1
        name = row.get("name", "").strip()
        name_norm = _normalise_name(name)
        const = row.get("constituency", "").strip().lower()
        matched = None
        method = ""
        score = 0.0

        # 1. Exact name match
        if name_norm in ref_by_name:
            matched = ref_by_name[name_norm]
            method, score = "exact", 1.0

        # 2. Constituency match
        if not matched and const and const in ref_by_const:
            matched = ref_by_const[const]
            method, score = "constituency", 1.0

        # 3. Token-set match (handles reversed names)
        if not matched:
            name_tokens = frozenset(name_norm.split())
            for ref_norm, ref_rec in ref_by_name.items():
                if frozenset(ref_norm.split()) == name_tokens:
                    matched = ref_rec
                    score = 0.95
                    method = "token-set"
                    break

        # 4. Fuzzy name match
        if not matched:
            hits = difflib.get_close_matches(
                name_norm, ref_names, n=1, cutoff=0.75
            )
            if hits:
                matched = ref_by_name[hits[0]]
                score = difflib.SequenceMatcher(
                    None, name_norm, hits[0]
                ).ratio()
                method = f"fuzzy({score:.2f})"

        # Skip non-MP roles
        if name_norm in NON_MP_ROLES:
            enriched.append(row)
            continue

        if matched:
            report["matched"] += 1
            report["methods"][method.split("(")[0]] += 1

            # Fill missing fields
            fill_map = {
                "party": "party_abbrev",
                "constituency": "constituency",
                "mp_id": "mp_id",
                "region": "region",
                "majority": "majority",
                "previous_mp": "previous_mp",
                "previous_party": "previous_party",
            }
            for hansard_col, ref_col in fill_map.items():
                if not row.get(hansard_col) and matched.get(ref_col):
                    row[hansard_col] = matched[ref_col]
                    if hansard_col in report["fields_filled"]:
                        report["fields_filled"][hansard_col] += 1

            row["match_score"] = f"{score:.2f}"
            row["match_method"] = method
        else:
            report["unmatched"].append(name)

        enriched.append(row)

    # Write output
    if output_path is None:
        stem = Path(hansard_path).stem.replace("_validated", "")
        output_path = str(Path(hansard_path).parent / f"{stem}_enriched.csv")

    if enriched:
        all_cols = list(enriched[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_cols)
            writer.writeheader()
            writer.writerows(enriched)
    print(f"  Enriched CSV saved → {output_path}")

    return enriched, dict(report), output_path


def print_enrichment_report(report: Dict, enriched: List[Dict],
                               report_path: str = None):
    """Print and save enrichment report."""
    sp = report["speaker_rows"]
    mat = report["matched"]
    pct = 100 * mat // sp if sp else 0

    lines = [
        "=" * 60,
        "HANSARD ENRICHMENT REPORT",
        "=" * 60,
        f"  Total rows          : {report['total_rows']:,}",
        f"  Stage direction rows: {report['stage_rows']:,}",
        f"  Speaker rows        : {sp:,}",
        f"  Matched to MP ref   : {mat:,} ({pct}%)",
        "",
        "  Match methods:",
    ]

    for method, count in report["methods"].items():
        lines.append(f"    {method:20s}: {count:,}")

    lines += ["", "  Fields filled by enrichment:"]
    for field, count in report["fields_filled"].items():
        lines.append(f"    {field:20s}: {count:,} rows")

    unmatched = sorted(set(report["unmatched"]))
    lines += [
        "",
        f"  Unmatched speakers ({len(unmatched)}):",
    ]
    for name in unmatched[:20]:  # Limit output
        lines.append(f"    - {name}")
    if len(unmatched) > 20:
        lines.append(f"    ... and {len(unmatched) - 20} more")

    lines += ["", "  Party distribution after enrichment:"]
    party_counts = Counter(
        r.get("party", "")
        for r in enriched
        if r.get("is_stage_direction") == "0" and r.get("party")
    )
    for party, cnt in party_counts.most_common():
        lines.append(f"    {party:12s}: {cnt:>4} rows")

    lines += ["", "=" * 60]

    output = "\n".join(lines)
    print("\n" + output)

    if report_path:
        Path(report_path).write_text(output + "\n", encoding="utf-8")
        print(f"\n  Report saved → {report_path}")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Enrich Hansard with MP reference data"
    )
    parser.add_argument(
        "hansard", help="Path to validated Hansard CSV"
    )
    parser.add_argument(
        "--ref", default="ghana_mps_9th_parliament.csv",
        help="Path to MP reference CSV"
    )
    parser.add_argument(
        "--out", default=None,
        help="Output path (default: auto-generated)"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Save enrichment report"
    )
    args = parser.parse_args()

    if not Path(args.ref).exists():
        print(f"ERROR: Reference file '{args.ref}' not found.")
        print("Run mp_reference.py first to build reference.")
        sys.exit(1)

    print(f"Enriching {args.hansard}…")
    enriched, report, out_csv = enrich_hansard(
        args.hansard, args.ref, args.out
    )

    if args.report:
        stem = Path(out_csv).stem
        report_path = str(Path(out_csv).parent / f"{stem}_report.txt")
        print_enrichment_report(report, enriched, report_path)
    else:
        print_enrichment_report(report, enriched, None)
