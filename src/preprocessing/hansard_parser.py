"""
Hansard Parser - Extract structured speaker turns from Hansard text.

This module parses Ghana Parliamentary Hansard documents into structured
speaker turns with metadata (party, constituency, debate type, etc.).
"""

import re
import csv
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
from collections import defaultdict


@dataclass
class Statement:
    """Represents a single speaker turn or stage direction in Hansard."""
    order: int
    speech_no: int
    page_no: int
    name: str
    title: str
    party: str
    constituency: str
    role: str
    debate_type: str
    debate_topic: str
    body: str
    is_stage_direction: int
    is_interjection: int
    is_question: int
    is_answer: int
    first_speech: int


# Regex patterns for parsing
_TITLES = (
    r"Mr|Mrs|Ms|Miss"
    r"|Dr|Prof(?:essor)?"
    r"|Alhaji|Hajia"
    r"|Rt\.?\s*Hon\.?"
    r"|The\s+Rt\.?\s*Hon\.?"
    r"|(?:The\s+)?Hon\.?"
    r"|Major|Colonel|Brigadier|General"
    r"|Lt\.?\s*Col\.?"
)
_NT = r"[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝ][A-Za-zÀ-ÿ'\-]+"
_NP = rf"(?:{_NT}(?:\s+{_NT})*)"
_PB = r"(?:\s*\([^)]*\))?"

SPEAKER_RE = re.compile(
    rf"^(?P<title>{_TITLES})\s+"
    rf"(?P<n>{_NP})"
    rf"(?P<party>{_PB})"
    r"(?:\s*\(MP\))?\s*:\s*",
)

ROLE_SPEAKER_RE = re.compile(
    rf"^(?P<role>[A-Z][A-Za-z\s,\-&/]+?)\s*"
    rf"\(\s*(?P<title>{_TITLES})\s+(?P<n>{_NP})\s*\)"
    r"(?:\s*\(MP\))?\s*:\s*",
)

SECTION_RE = re.compile(
    r"^(STATEMENT|MOTION|RESOLUTION|PAPER|QUESTION\s+TIME"
    r"|ANNOUNCEMENT|CLOSING\s+REMARKS?"
    r"|ADJOURNMENT"
    r"|VOTES\s+AND\s+PROCEEDINGS(?:\s+AND\s+THE\s+OFFICIAL\s+REPORT)?"
    r"|FIRST\s+READING|SECOND\s+READING|THIRD\s+READING"
    r"|CONSIDERATION\s+STAGE|BUSINESS\s+OF\s+THE\s+HOUSE)\s*",
)

RUNNING_HEAD_RE = re.compile(
    r"^(?:"
    r"Statement|Motion|Resolution|Paper"
    r"|Closing Remarks?"
    r"|Votes And Proceedings.*?"
    r"|Announcement"
    r"|(?:First|Second|Third) Reading"
    r"|Consideration Stage"
    r")\s*",
    re.IGNORECASE,
)

INLINE_SECTION_RE = re.compile(
    r"(?:^|\s)(STATEMENT|MOTION|RESOLUTION|PAPER|ANNOUNCEMENT"
    r"|CLOSING\s+REMARKS?|ADJOURNMENT)\s*",
)

PAGE_RE = re.compile(r"^---\s*Page\s+(\d+)\s*---\s*$", re.IGNORECASE)

COL_HDR_RE = re.compile(
    r"^\d+\s+\d{1,2}(?:st|nd|rd|th)\s+\w+\s*,?\s*\d{4}\s+\d+$"
)

STAGE_RE = re.compile(
    r"^\[.*?\]\s*$"
    r"|\bThe\s+House\s+(met|was\s+adjourned|divided)\b"
    r"|\bQuestion\s+(agreed\s+to|put\s+and\s+agreed\s+to|negatived)\b"
    r"|\bBill\s+read\s+a\s+(first|second|third)\s+time\b"
    r"|\bMotion\s+agreed\s+to\b"
    r"|\bResolution\s+agreed\s+to\b"
    r"|\bDebate\s+adjourned\b"
    r"|\(Time\s+expired\)"
    r"|\bHear!\s*Hear!\b"
    r"|\bOrder!\s*(?:Order!)?\b"
    r"|\bAdjourned\s+sine\s+die\b",
    re.IGNORECASE,
)

PRESIDING_RE = re.compile(
    r"\bSpeaker\b|\bDeputy\s+Speaker\b|\bChair(?:man)?\b",
    re.IGNORECASE,
)

_HYPHEN_NORM_RE = re.compile(r"(?<=[A-Za-z]) -(?=[A-Z])")


def _norm_hyphens(text: str) -> str:
    """Normalize hyphenated names split across lines."""
    return _HYPHEN_NORM_RE.sub("-", text)


def preprocess(raw: str) -> Tuple[List[str], List[int]]:
    """
    Convert raw PDF-export text to logical lines with page numbers.
    
    Args:
        raw: Raw text extracted from PDF
        
    Returns:
        Tuple of (logical_lines, page_numbers)
    """
    raw_lines = raw.splitlines()
    out_lines = []
    line_pages = []
    current_page = 0
    pending = ""
    pending_page = 0

    def flush():
        nonlocal pending, pending_page
        s = _norm_hyphens(pending.strip())
        if s:
            out_lines.append(s)
            line_pages.append(pending_page)
        pending = ""
        pending_page = current_page

    for raw_line in raw_lines:
        stripped = raw_line.strip()

        pm = PAGE_RE.match(stripped)
        if pm:
            flush()
            current_page = int(pm.group(1))
            out_lines.append(stripped)
            line_pages.append(current_page)
            pending_page = current_page
            continue

        if not stripped or COL_HDR_RE.match(stripped):
            flush()
            continue

        if SECTION_RE.match(stripped):
            flush()
            out_lines.append(stripped)
            line_pages.append(current_page)
            continue

        if RUNNING_HEAD_RE.match(stripped):
            flush()
            continue

        im = INLINE_SECTION_RE.search(stripped)
        if im:
            before = stripped[:im.start(1)].strip()
            heading = im.group(1).strip().upper()
            if before:
                pending += (" " if pending else "") + before
            flush()
            out_lines.append(heading)
            line_pages.append(current_page)
            continue

        # Test normalised form so "Asante -Boateng:" matches SPEAKER_RE
        stripped_norm = _norm_hyphens(stripped)
        starts_speaker = (
            SPEAKER_RE.match(stripped_norm) is not None
            or ROLE_SPEAKER_RE.match(stripped_norm) is not None
        )
        if starts_speaker:
            flush()
            pending = stripped_norm
            pending_page = current_page
            continue

        if stripped.startswith("[") and STAGE_RE.search(stripped):
            flush()
            out_lines.append(stripped)
            line_pages.append(current_page)
            continue

        if pending:
            if pending.endswith("-"):
                pending = pending[:-1] + stripped
            else:
                pending += " " + stripped
        else:
            pending = stripped
            pending_page = current_page

    flush()
    return out_lines, line_pages


def match_speaker(line: str) -> Optional[Tuple[str, str, str, str, str]]:
    """Extract speaker info from a line."""
    m = ROLE_SPEAKER_RE.match(line)
    if m:
        return (
            m.group("title").strip(),
            m.group("n").strip(),
            "",
            m.group("role").strip(" ,"),
            line[m.end():],
        )
    m = SPEAKER_RE.match(line)
    if m:
        return (
            m.group("title").strip(),
            m.group("n").strip(),
            (m.group("party") or "").strip(),
            "",
            line[m.end():],
        )
    return None


def parse_party_block(block: str) -> Tuple[str, str]:
    """Parse party and constituency from block like '(NPP - Constituency)'."""
    b = block.strip("() ")
    for sep in ("—", "–", "-"):
        if sep in b:
            p, c = b.split(sep, 1)
            return p.strip(), c.strip()
    return b.strip(), ""


def clean_body(text: str) -> str:
    """Clean extracted body text."""
    text = PAGE_RE.sub("", text)
    lines = [l for l in text.splitlines() if not COL_HDR_RE.match(l.strip())]
    text = " ".join(l.strip() for l in lines if l.strip())
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _name_key(name: str) -> str:
    """Canonical key for fuzzy matching."""
    return re.sub(r"-", " ", name).lower().strip()


def split_midline_interjections(statements: List[Statement]) -> List[Statement]:
    """
    Split mid-line interjections embedded within a body.
    
    Example: "...because it is — Mr First Deputy Speaker: You cannot do that."
    """
    _TITLES_PAT = (
        r"Mr|Mrs|Ms|Miss|Dr|Prof(?:essor)?|Alhaji|Hajia|Hon\.?[\s*MP]?"
    )
    _NT = r"[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝ][A-Za-zÀ-ÿ'\-]+"
    _NP = rf"(?:{_NT}(?:\s+{_NT})*)"
    MID = re.compile(
        rf"(?:—|--|\s)\s*(?P<title>{_TITLES_PAT})\s+(?P<n>{_NP})\s*:\s*"
    )

    result = []
    for s in statements:
        m = MID.search(s.body)
        if m:
            before = s.body[:m.start()].strip()
            after = s.body[m.end():].strip()

            # Truncated main statement
            main = Statement(**asdict(s))
            main.body = before
            result.append(main)

            # Interjection row
            inj = Statement(**asdict(s))
            inj.name = m.group("n").strip()
            inj.title = m.group("title").strip()
            inj.party = ""
            inj.constituency = ""
            inj.role = ""
            inj.body = after
            inj.is_interjection = 1
            inj.first_speech = 0
            result.append(inj)
        else:
            result.append(s)

    # Re-number order sequentially
    for i, s in enumerate(result, start=1):
        s.order = i

    return result


class HansardParser:
    """Parse Ghana Parliamentary Hansard text into structured speaker turns."""

    def __init__(self, filepath: str):
        """
        Initialize parser with Hansard text file.
        
        Args:
            filepath: Path to .txt file extracted from PDF
        """
        self.filepath = Path(filepath)
        raw = self.filepath.read_text(encoding="utf-8", errors="replace")

        self.statements: List[Statement] = []
        self.date = ""
        self.parliament = "Parliament of Ghana"

        # Extract date from header
        m = re.search(r"Date:\s*(.+)", raw)
        if m:
            self.date = m.group(1).strip()

        self._lines, self._pages = preprocess(raw)

        self._order = 0
        self._speech_no = 0
        self._current_page = 0
        self._debate_type = "GENERAL"
        self._debate_topic = ""
        self._prev_speaker = None
        self._registry: Dict[Tuple[str, str], Dict] = {}
        self._first_seen = set()

        self._parse()
        self._flag_interjections()
        self._flag_q_and_a()
        self.statements = split_midline_interjections(self.statements)

    def _reg_key(self, title: str, name: str) -> Tuple[str, str]:
        """Generate registry key."""
        return (title.lower(), _name_key(name))

    def _register(self, title: str, name: str, party_block: str, role: str) -> Dict:
        """Register speaker in registry."""
        party, constituency = (
            parse_party_block(party_block) if party_block else ("", "")
        )
        info = {
            "name": name,
            "title": title,
            "party": party,
            "constituency": constituency,
            "role": role,
        }
        self._registry[self._reg_key(title, name)] = info
        # Also index by surname only for fuzzy matching
        parts = name.split()
        if len(parts) > 1:
            self._registry.setdefault(self._reg_key(title, parts[-1]), info)
        return info

    def _resolve(self, title: str, name: str, party_block: str, role: str) -> Dict:
        """Resolve speaker from registry or create new entry."""
        key = self._reg_key(title, name)
        if key in self._registry:
            info = self._registry[key]
            if party_block:
                p, c = parse_party_block(party_block)
                if p and not info["party"]:
                    info["party"] = p
                if c and not info["constituency"]:
                    info["constituency"] = c
            if role and not info["role"]:
                info["role"] = role
            return info
        return self._register(title, name, party_block, role)

    def _parse(self):
        """Main parsing loop."""
        i = 0
        while i < len(self._lines):
            line = self._lines[i]

            pm = PAGE_RE.match(line)
            if pm:
                self._current_page = int(pm.group(1))
                i += 1
                continue

            if SECTION_RE.match(line):
                heading = line.strip().upper()
                if "CLOSING" in heading:
                    heading = "CLOSING REMARKS"
                elif "VOTES AND PROCEEDINGS" in heading:
                    heading = "VOTES AND PROCEEDINGS"
                self._debate_type = heading

                # Extract topic (lines until next speaker or section)
                topic_parts = []
                j = i + 1
                while j < len(self._lines):
                    tl = self._lines[j].strip()
                    if not tl:
                        j += 1
                        continue
                    if (
                        PAGE_RE.match(tl)
                        or SECTION_RE.match(tl)
                        or match_speaker(tl) is not None
                        or (tl.startswith("[") and STAGE_RE.search(tl))
                    ):
                        break
                    topic_parts.append(tl)
                    j += 1

                if topic_parts:
                    raw_topic = " ".join(topic_parts)
                    raw_topic = re.sub(r"-\s+", "", raw_topic)
                    self._debate_topic = raw_topic.strip()
                else:
                    self._debate_topic = ""

                self._prev_speaker = None
                i += 1
                continue

            if line.startswith("[") and STAGE_RE.search(line):
                self._order += 1
                self.statements.append(Statement(
                    order=self._order,
                    speech_no=self._speech_no,
                    page_no=self._current_page,
                    name="stage direction",
                    title="",
                    party="",
                    constituency="",
                    role="",
                    debate_type=self._debate_type,
                    debate_topic=self._debate_topic,
                    body=clean_body(line),
                    is_stage_direction=1,
                    is_interjection=0,
                    is_question=0,
                    is_answer=0,
                    first_speech=0,
                ))
                i += 1
                continue

            result = match_speaker(line)
            if result:
                title, name, party_block, role, body_raw = result
                info = self._resolve(title, name, party_block, role)
                body = clean_body(body_raw)

                if not body:
                    i += 1
                    continue

                full_name = info["name"]
                if full_name != self._prev_speaker:
                    self._speech_no += 1
                    self._prev_speaker = full_name

                first_sp = 0
                if full_name not in self._first_seen:
                    first_sp = 1
                    self._first_seen.add(full_name)

                self._order += 1
                is_stage = int(STAGE_RE.search(body) is not None)

                self.statements.append(Statement(
                    order=self._order,
                    speech_no=self._speech_no,
                    page_no=self._current_page,
                    name=full_name,
                    title=info["title"],
                    party=info["party"],
                    constituency=info["constituency"],
                    role=info["role"],
                    debate_type=self._debate_type,
                    debate_topic=self._debate_topic,
                    body=body,
                    is_stage_direction=is_stage,
                    is_interjection=0,
                    is_question=0,
                    is_answer=0,
                    first_speech=first_sp,
                ))
                i += 1
                continue

            i += 1

    def _flag_interjections(self):
        """Flag interjections based on speaker changes within speech."""
        groups = defaultdict(list)
        for s in self.statements:
            groups[s.speech_no].append(s)

        for stmts in groups.values():
            main = next(
                (s.name for s in stmts if not s.is_stage_direction and s.name),
                None,
            )
            if not main:
                continue
            for s in stmts:
                if s.is_stage_direction:
                    continue
                if s.name == main or PRESIDING_RE.search(s.name):
                    s.is_interjection = 0
                else:
                    s.is_interjection = 1

    def _flag_q_and_a(self):
        """Flag questions and answers during Question Time."""
        for i, s in enumerate(self.statements):
            if s.debate_type != "QUESTION TIME":
                continue
            if s.is_stage_direction or PRESIDING_RE.search(s.name):
                continue
            if s.body.rstrip().endswith("?"):
                s.is_question = 1
            elif i > 0 and self.statements[i - 1].is_question == 1:
                s.is_answer = 1

    def to_csv(self, output_path: str):
        """Export parsed statements to CSV."""
        output_path = Path(output_path)
        if not self.statements:
            print("Warning: no statements found.")
            return

        fieldnames = list(asdict(self.statements[0]).keys())
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for s in self.statements:
                writer.writerow(asdict(s))
        print(f"Wrote {len(self.statements):,} rows -> {output_path}")

    def print_summary(self):
        """Print parsing summary."""
        total = len(self.statements)
        stage = sum(1 for s in self.statements if s.is_stage_direction)
        interj = sum(1 for s in self.statements if s.is_interjection)
        speeches = len({s.speech_no for s in self.statements})
        speakers = {s.name for s in self.statements if not s.is_stage_direction}

        debate_counts = {}
        for s in self.statements:
            debate_counts[s.debate_type] = debate_counts.get(s.debate_type, 0) + 1

        topic_counts = {}
        for s in self.statements:
            if s.debate_topic:
                topic_counts[s.debate_topic] = topic_counts.get(s.debate_topic, 0) + 1

        W = 74
        print("\n" + "=" * W)
        print("  HANSARD PARSER - SUMMARY")
        print("=" * W)
        print(f"  File           : {self.filepath.name}")
        print(f"  Date           : {self.date}")
        print(f"  Parliament     : {self.parliament}")
        print(f"  Total rows     : {total:,}")
        print(f"  Speech turns   : {speeches:,}")
        print(f"  Unique speakers: {len(speakers):,}")
        print(f"  Stage dirs     : {stage:,}")
        print(f"  Interjections  : {interj:,}")
        print(f"\n  Rows by debate type:")
        for dt, cnt in sorted(debate_counts.items(), key=lambda x: -x[1]):
            print(f"    {dt:<44} {cnt:>4}")
        print(f"\n  Debate topics (by row count):")
        for tp, cnt in sorted(topic_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"    [{cnt:>3}]  {tp[:66]}")
        print("=" * W + "\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        in_path = sys.argv[1]
    else:
        print("Usage: python hansard_parser.py <input_txt_file>")
        sys.exit(1)

    out_path = in_path.replace(".txt", "_parsed.csv")
    print(f"Parsing: {in_path}")
    parser = HansardParser(in_path)
    parser.print_summary()
    parser.to_csv(out_path)
