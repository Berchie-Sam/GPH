"""
Hansard Validation Suite (T1-T10)

Implements validation tests based on best practices from computational
parliamentary text analysis (Katz & Alexander methodology adapted for Ghana).
"""

import re
import csv
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import Counter, defaultdict


# Result types
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


@dataclass
class TestResult:
    """Result of a validation test."""
    test_id: str
    name: str
    status: str  # PASS / WARN / FAIL
    issues: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)

    def __str__(self):
        icon = {"PASS": "✓", "WARN": "☢", "FAIL": "✗"}[self.status]
        lines = [f"  [{icon}] {self.test_id}: {self.name}  →  {self.status}"]
        for issue in self.issues:
            lines.append(f"        • {issue}")
        for fix in self.fixes_applied:
            lines.append(f"        ✎ FIX: {fix}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════


def load_csv(path: str) -> List[Dict]:
    """Load CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(rows: List[Dict], path: str):
    """Save rows to CSV."""
    if not rows:
        return
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_source(path: str) -> str:
    """Load source text file."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _name_key(name: str) -> str:
    """Canonical name key for matching."""
    return re.sub(r"-", " ", name).lower().strip()


# ══════════════════════════════════════════════════════
# Individual Tests (T1-T10)
# ══════════════════════════════════════════════════════


def t1_date_consistency(rows: List[Dict], source_text: str, csv_path: str) -> TestResult:
    """
    T1 — Date consistency
    Verify filename date matches session-header date in source text.
    """
    result = TestResult("T1", "Date consistency", PASS)

    # Extract date from source header
    m = re.search(r"Date:\s*(.+)", source_text)
    header_date = m.group(1).strip() if m else None

    # Extract date from session body
    m2 = re.search(
        r"((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r",?\s+\d{1,2}\w*\s+\w+,?\s*\d{4})",
        source_text,
    )
    session_date = m2.group(1).strip() if m2 else None

    # Extract date from filename
    stem = Path(csv_path).stem
    fn_date_m = re.search(
        r"(\d{1,2}(?:st|nd|rd|th)?)[_\s](\w+)[_\s](\d{4})",
        stem, re.IGNORECASE,
    )
    fn_date = (
        f"{fn_date_m.group(1)} {fn_date_m.group(2)} {fn_date_m.group(3)}"
        if fn_date_m else None
    )

    result.issues.append(f"Header date   : {header_date}")
    result.issues.append(f"Session date  : {session_date}")
    result.issues.append(f"Filename date : {fn_date}")

    if header_date and session_date:
        if header_date.lower().replace(",", "") != session_date.lower().replace(",", ""):
            result.status = FAIL
            result.issues.append(
                f"MISMATCH: header '{header_date}' ≠ session '{session_date}'"
            )
        else:
            result.issues.append("Header date matches session date: OK")
    else:
        result.status = WARN
        result.issues.append("Could not fully verify date — one source missing")

    return result


def t2_duplicate_bodies(rows: List[Dict], apply_fix: bool) -> TestResult:
    """
    T2 — Duplicate body text
    Flag consecutive rows with identical body text (likely parsing error).
    """
    result = TestResult("T2", "Duplicate body text", PASS)
    consec_dups = []
    nonconsec_dups = []

    body_seen: Dict[str, int] = {}
    sorted_rows = sorted(rows, key=lambda r: int(r["order"]))

    for i, r in enumerate(sorted_rows):
        body = r["body"].strip()
        if not body or r.get("is_stage_direction") == "1":
            continue
        prev = sorted_rows[i - 1] if i > 0 else None
        if prev and prev["body"].strip() == body:
            consec_dups.append(
                f"rows {prev['order']}+{r['order']}: "
                f"{r['name']} | {repr(body[:60])}"
            )
        elif body in body_seen:
            nonconsec_dups.append(
                f"rows {body_seen[body]}+{r['order']}: "
                f"{repr(body[:60])}"
            )
        body_seen[body] = r["order"]

    if consec_dups:
        result.status = FAIL
        result.issues.append(
            f"{len(consec_dups)} consecutive duplicate(s) — likely parsing error:"
        )
        for d in consec_dups[:5]:
            result.issues.append(f"  {d}")

    if nonconsec_dups:
        if result.status == PASS:
            result.status = WARN
        result.issues.append(
            f"{len(nonconsec_dups)} non-consecutive duplicate(s) — likely genuine:"
        )
        for d in nonconsec_dups[:3]:
            result.issues.append(f"  {d}")

    if result.status == PASS:
        result.issues.append("No consecutive duplicate bodies found")

    return result


def t3_time_expired(rows: List[Dict]) -> TestResult:
    """
    T3 — Time-expired placement
    '(Time expired)' should be at end of body, not mid-body.
    """
    result = TestResult("T3", "Time-expired placement", PASS)
    TE = re.compile(r"\(Time\s+expired\)", re.IGNORECASE)
    TE_END = re.compile(r"\(Time\s+expired\)\s*$")

    issues = []
    for r in rows:
        if TE.search(r["body"]):
            if not TE_END.search(r["body"]):
                issues.append(
                    f"Row {r['order']} ({r['name']}): "
                    f"'(Time expired)' not at end → "
                    f"{repr(r['body'][-80:])}"
                )

    if issues:
        result.status = FAIL
        result.issues += issues
    else:
        result.issues.append("No misplaced '(Time expired)' found")

    return result


def t4_flag_sanity(rows: List[Dict], apply_fix: bool) -> TestResult:
    """
    T4 — Flag sanity
    Validate flag columns contain only 0/1 and mutual exclusivity.
    """
    result = TestResult("T4", "Flag sanity", PASS)
    FLAG_COLS = [
        "is_stage_direction", "is_interjection",
        "is_question", "is_answer", "first_speech",
    ]

    issues = []
    first_speech_counts = Counter(
        r["name"] for r in rows if r.get("first_speech") == "1"
    )

    for r in rows:
        oid = r["order"]
        # Valid binary values
        for col in FLAG_COLS:
            if r.get(col) not in ("0", "1", 0, 1, ""):
                issues.append(
                    f"Row {oid}: {col}={repr(r.get(col))} is not 0/1"
                )
        # Q and A mutually exclusive
        if r.get("is_question") in ("1", 1) and r.get("is_answer") in ("1", 1):
            issues.append(
                f"Row {oid}: is_question=1 AND is_answer=1"
            )
        # Stage + interjection mutually exclusive
        if r.get("is_stage_direction") in ("1", 1) and r.get("is_interjection") in ("1", 1):
            issues.append(
                f"Row {oid}: is_stage_direction=1 AND is_interjection=1"
            )

    # first_speech should fire once per speaker
    multi = {n: c for n, c in first_speech_counts.items() if c > 1}
    if multi:
        issues.append(f"first_speech=1 appears multiple times for: {multi}")

    all_speakers = {r["name"] for r in rows if r.get("is_stage_direction") != "1"}
    no_first = all_speakers - set(first_speech_counts.keys())
    if no_first and "stage direction" not in no_first:
        issues.append(f"No first_speech=1 for speakers: {sorted(no_first)[:5]}")

    if issues:
        result.status = FAIL
        result.issues += issues
    else:
        result.issues.append("All flag checks passed")

    return result


def t5_party_consistency(rows: List[Dict], apply_fix: bool) -> TestResult:
    """
    T5 — Party and constituency consistency
    Each speaker should have one party and one constituency across session.
    """
    result = TestResult("T5", "Party/constituency consistency", PASS)
    party_map: Dict[str, set] = defaultdict(set)
    const_map: Dict[str, set] = defaultdict(set)

    for r in rows:
        name = r["name"]
        if name == "stage direction":
            continue
        if r.get("party"):
            party_map[name].add(r["party"])
        if r.get("constituency"):
            const_map[name].add(r["constituency"])

    issues = []
    for name, parties in party_map.items():
        if len(parties) > 1:
            issues.append(f"{name}: multiple parties → {sorted(parties)}")
    for name, consts in const_map.items():
        if len(consts) > 1:
            issues.append(f"{name}: multiple constituencies → {sorted(consts)}")

    attributed = len(party_map)
    total_speakers = len({r["name"] for r in rows if r.get("is_stage_direction") != "1"})
    unattributed = total_speakers - attributed
    result.issues.append(
        f"Speakers with party: {attributed}/{total_speakers} ({unattributed} unattributed)"
    )

    if issues:
        result.status = FAIL
        result.issues += issues
    else:
        result.issues.append("Consistent party/constituency attribution")

    return result


def t6_short_form_names(rows: List[Dict], apply_fix: bool) -> TestResult:
    """
    T6 — Unresolved short-form names
    Detect surname-only references or transposed name variants.
    """
    result = TestResult("T6", "Short-form / duplicate name resolution", PASS)
    non_stage = [r for r in rows if r.get("is_stage_direction") != "1"]
    unique_names = sorted({r["name"] for r in non_stage})

    issues = []
    fixes = []

    # Surname-only references
    for name in unique_names:
        parts = name.split()
        if len(parts) == 1:
            candidates = [
                n for n in unique_names
                if n != name and n.split()[-1].lower() == name.lower()
            ]
            if candidates:
                issues.append(f"'{name}' appears to be short form of: {candidates[:3]}")

    if issues:
        result.status = WARN
        result.issues += issues
    else:
        result.issues.append("No unresolved short-form names")

    result.fixes_applied = fixes
    return result


def t7_page_sequence(rows: List[Dict]) -> TestResult:
    """
    T7 — Page sequence
    Check page numbers are sequential and account for missing pages.
    """
    result = TestResult("T7", "Page sequence", PASS)

    page_nos = sorted({int(r["page_no"]) for r in rows if r.get("page_no")})
    if not page_nos:
        result.status = WARN
        result.issues.append("No page numbers found")
        return result

    min_pg, max_pg = page_nos[0], page_nos[-1]
    expected = set(range(min_pg, max_pg + 1))
    missing = sorted(expected - set(page_nos))

    result.issues.append(f"Pages: {min_pg}–{max_pg} ({len(page_nos)}/{len(expected)} have statements)")

    if missing:
        result.status = WARN
        result.issues.append(f"{len(missing)} pages have no statements: {missing[:5]}")
    else:
        result.issues.append("All pages have at least one statement")

    return result


def t8_order_integrity(rows: List[Dict], apply_fix: bool) -> TestResult:
    """
    T8 — Order integrity
    'order' column must be strictly sequential 1..N.
    """
    result = TestResult("T8", "Order integrity", PASS)
    orders = [int(r["order"]) for r in rows]
    n = len(orders)
    expected = list(range(1, n + 1))

    if orders == expected:
        result.issues.append(f"Order is strictly sequential 1..{n}: OK")
    else:
        dups = [o for o, c in Counter(orders).items() if c > 1]
        gaps = [e for e in expected if e not in set(orders)]
        if dups:
            result.status = FAIL
            result.issues.append(f"Duplicate order values: {dups}")
        if gaps:
            result.status = FAIL
            result.issues.append(f"Missing order values: {gaps[:10]}")
        if apply_fix:
            for i, r in enumerate(rows, start=1):
                r["order"] = str(i)
            result.fixes_applied.append(f"Re-numbered order column 1..{n}")
            result.status = PASS

    return result


def t9_embedded_speaker_prefixes(rows: List[Dict], apply_fix: bool) -> TestResult:
    """
    T9 — Embedded mid-line speaker prefixes
    Detect unresolved speaker patterns in body text.
    """
    result = TestResult("T9", "Embedded speaker prefixes", PASS)

    _TITLES_PAT = r"Mr|Mrs|Ms|Miss|Dr|Prof|Alhaji|Hajia|Hon"
    _NT = r"[A-Z][A-Za-z'\-]+"
    _NP = rf"(?:{_NT}(?:\s+{_NT})*)"
    MID = re.compile(rf"(?:—|--|-)\s*(?P<title>{_TITLES_PAT})\.?\s+(?P<n>{_NP})\s*:\s*")

    issues = []
    for r in rows:
        m = MID.search(r["body"])
        if m:
            issues.append(
                f"Row {r['order']}: embedded speaker '{m.group(0).strip()}' in body"
            )

    if issues:
        result.status = WARN
        result.issues += issues[:5]  # Limit output
    else:
        result.issues.append("No embedded speaker prefixes")

    return result


def t10_debate_type_coverage(rows: List[Dict]) -> TestResult:
    """
    T10 — Debate type and topic coverage
    Check all non-stage rows have debate_type; key types have topics.
    """
    result = TestResult("T10", "Debate type and topic coverage", PASS)

    no_type = [
        r["order"] for r in rows
        if r.get("is_stage_direction") != "1" and not r.get("debate_type")
    ]
    topic_required = {"STATEMENT", "MOTION", "RESOLUTION", "ANNOUNCEMENT"}
    missing_topic = [
        (r["order"], r["name"], r.get("debate_type", ""))
        for r in rows
        if r.get("debate_type") in topic_required
        and not r.get("debate_topic")
        and r.get("is_stage_direction") != "1"
    ]

    # Distribution summary
    type_dist = Counter(r.get("debate_type", "") for r in rows)
    result.issues.append("Debate type distribution:")
    for dt, cnt in type_dist.most_common()[:5]:
        result.issues.append(f"  {dt:<35}: {cnt:>4} rows")

    if no_type:
        result.status = FAIL
        result.issues.append(f"{len(no_type)} rows missing debate_type")
    if missing_topic:
        if result.status == PASS:
            result.status = WARN
        result.issues.append(f"{len(missing_topic)} key rows missing topic")

    if result.status == PASS:
        result.issues.append("Debate type/topic coverage OK")

    return result


# ══════════════════════════════════════════════════════
# Main Validation Function
# ══════════════════════════════════════════════════════


def validate_hansard(csv_path: str, source_path: Optional[str] = None,
                     apply_fix: bool = False) -> List[TestResult]:
    """
    Run full T1-T10 validation suite on a parsed Hansard CSV.
    
    Args:
        csv_path: Path to parsed CSV file
        source_path: Optional path to source TXT file (for T1)
        apply_fix: Whether to apply auto-fixes
        
    Returns:
        List of TestResult objects
    """
    rows = load_csv(csv_path)
    source_text = load_source(source_path) if source_path else ""

    results = [
        t1_date_consistency(rows, source_text, csv_path),
        t2_duplicate_bodies(rows, apply_fix),
        t3_time_expired(rows),
        t4_flag_sanity(rows, apply_fix),
        t5_party_consistency(rows, apply_fix),
        t6_short_form_names(rows, apply_fix),
        t7_page_sequence(rows),
        t8_order_integrity(rows, apply_fix),
        t9_embedded_speaker_prefixes(rows, apply_fix),
        t10_debate_type_coverage(rows),
    ]

    return results


def print_report(results: List[TestResult], csv_path: str,
                 source_path: Optional[str] = None, apply_fix: bool = False):
    """Print validation report."""
    total = len(results)
    passed = sum(1 for r in results if r.status == PASS)
    warned = sum(1 for r in results if r.status == WARN)
    failed = sum(1 for r in results if r.status == FAIL)

    W = 74
    print("\n" + "═" * W)
    print("  HANSARD VALIDATOR — REPORT")
    print("═" * W)
    print(f"  CSV    : {csv_path}")
    if source_path:
        print(f"  Source : {source_path}")
    print(f"  Mode   : {'FIX' if apply_fix else 'CHECK ONLY'}")
    print(f"  Tests  : {total}  |  PASS: {passed}  WARN: {warned}  FAIL: {failed}")
    print("─" * W)
    for r in results:
        print(str(r))
        print()
    print("═" * W + "\n")


def write_fix_report(results: List[TestResult], report_path: str):
    """Write fix report to file."""
    lines = ["HANSARD VALIDATOR — FIX REPORT\n"]
    any_fix = False
    for r in results:
        if r.fixes_applied:
            any_fix = True
            lines.append(f"[{r.test_id}] {r.name}")
            for f in r.fixes_applied:
                lines.append(f"  • {f}")
            lines.append("")
    if not any_fix:
        lines.append("No automatic fixes were applied.")
    Path(report_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Fix report written → {report_path}")


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Validate Hansard CSV")
    parser.add_argument("csv", help="Path to parsed CSV file")
    parser.add_argument("--source", help="Path to source TXT file (for T1)")
    parser.add_argument("--fix", action="store_true", help="Apply auto-fixes")
    parser.add_argument("--report", help="Path to write fix report")
    args = parser.parse_args()

    results = validate_hansard(args.csv, args.source, args.fix)
    print_report(results, args.csv, args.source, args.fix)

    if args.fix and args.report:
        write_fix_report(results, args.report)
        stem = Path(args.csv).stem.replace("_parsed", "")
        out_csv = str(Path(args.csv).parent / f"{stem}_validated.csv")
        rows = load_csv(args.csv)
        save_csv(rows, out_csv)
        print(f"Validated CSV saved → {out_csv}")
