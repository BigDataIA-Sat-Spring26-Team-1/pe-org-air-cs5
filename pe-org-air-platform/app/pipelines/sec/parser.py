from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional, List

import pdfplumber
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


class SecParser:
    """
    SEC filing section extractor.

    What it does:
    1) Reads HTML/TXT/PDF into text
    2) Finds section headings (Item-based + a few robust variants)
    3) Extracts section text from heading -> next heading (or end marker)

    Key robustness upgrades vs naive versions:
    - Keeps newlines (critical for detecting headings vs inline cross-references)
    - Avoids Table-of-Contents hits
    - Avoids inline cross-references like "...included in Part I, Item 2..."
    - Adds correct 10-Q end markers (Item 3/4, Part II)
    - Safe fallback to older behavior if scoring can't decide
    """

    def __init__(self) -> None:
        # NOTE: These patterns are intentionally "strong signals" (Item-based),
        # plus a couple robust variants for common punctuation/dash differences.
        # We avoid matching plain "Business" without Item number to prevent false positives.
        self.PATTERNS_BY_FORM: Dict[str, Dict[str, List[str]]] = {
            "10-K": {
                "Business": [
                    r"Item\s*1[\.\-–:]?\s*Business",
                    r"ITEM\s*1[\.\-–:]?\s*BUSINESS",
                    r"Business\s+Description",
                    r"Item\s*1\.?\s*Business\s+Description",
                ],
                "Risk Factors": [
                    r"Item\s*1A[\.\-–:]?\s*Risk\s*Factors",
                    r"ITEM\s*1A[\.\-–:]?\s*RISK\s*FACTORS",
                    r"Risk\s+Factors",
                ],
                "MD&A": [
                    r"Item\s*7[\.\-–:]?\s*Management[’']?s?\s+Discussion\s+and\s+Analysis",
                    r"ITEM\s*7[\.\-–:]?\s*MANAGEMENT[’']?S?\s+DISCUSSION\s+AND\s+ANALYSIS",
                ],
            },
            "10-Q": {
                "MD&A": [
                    r"Item\s*2[\.\-–:]?\s*Management[’']?s?\s+Discussion\s+and\s+Analysis",
                    r"ITEM\s*2[\.\-–:]?\s*MANAGEMENT[’']?S?\s+DISCUSSION\s+AND\s+ANALYSIS",
                    # light fallback (kept, but not too broad)
                    r"Item\s*2[\.\-–:]?\s*Management",
                    r"ITEM\s*2[\.\-–:]?\s*MANAGEMENT",
                ],
                "Risk Factors": [
                    r"Item\s*1A[\.\-–:]?\s*Risk\s*Factors",
                    r"ITEM\s*1A[\.\-–:]?\s*RISK\s*FACTORS",
                ],
            },
            "8-K": {
                "Events": [
                    r"Item\s*8\.01",
                    r"Item\s*5\.02",
                    r"Item\s*1\.01",
                    r"ITEM\s*8\.01",
                    r"ITEM\s*5\.02",
                    r"ITEM\s*1\.01",
                ]
            },
            "DEF 14A": {
                "CD&A": [
                    r"COMPENSATION\s+DISCUSSION\s+(?:AND|&)\s+ANALYSIS",
                ],
                "Summary Tables": [
                    r"SUMMARY\s+COMPENSATION\s+TABLE",
                    r"EXECUTIVE\s+COMPENSATION\s+TABLES",
                ],
                "Incentive Plan": [
                    r"ANNUAL\s+INCENTIVE\s+PLAN",
                    r"LONG-TERM\s+INCENTIVE",
                ],
            },
        }

    # ----------------------------
    # Public API
    # ----------------------------
    def parse(self, file_path: Path, form_type: str) -> Dict[str, str]:
        """
        Parse a local filing and return extracted sections for the given form type.
        """
        text = ""
        suffix = file_path.suffix.lower()

        try:
            if suffix in [".html", ".htm", ".txt"]:
                raw_content = file_path.read_text(encoding="utf-8", errors="ignore")

                if "<html" in raw_content.lower() or "<xml" in raw_content.lower():
                    soup = BeautifulSoup(raw_content, "lxml")
                    for script in soup(["script", "style"]):
                        script.extract()
                    # Preserve newlines so headings remain headings
                    text = soup.get_text(separator="\n")
                else:
                    text = raw_content

            elif suffix == ".pdf":
                with pdfplumber.open(file_path) as pdf:
                    # Preserve page breaks with newlines
                    pages = [(p.extract_text() or "") for p in pdf.pages]
                    text = "\n\n".join(pages)

            else:
                logger.warning("unsupported_file_type", path=str(file_path), suffix=suffix)
                return {}

        except Exception as e:
            logger.error("file_read_error", path=str(file_path), error=str(e))
            return {}

        clean_text = self._normalize_text(text)
        return self._extract_sections(clean_text, form_type)

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _normalize_text(self, text: str) -> str:
        """
        Normalize without destroying line structure.
        This is critical for distinguishing headings from inline references.
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # collapse runs of spaces/tabs, keep newlines
        text = re.sub(r"[ \t\f\v]+", " ", text)
        # collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_sections(self, text: str, form_type: str) -> Dict[str, str]:
        patterns = self.PATTERNS_BY_FORM.get(form_type, {})
        if not patterns:
            logger.warning("unknown_form_type", form_type=form_type)
            return {}

        results: Dict[str, str] = {}

        # Build end markers (prefer line-start matches)
        end_patterns = self._build_end_patterns(form_type, patterns)

        for section_name, specific_patterns in patterns.items():
            matches: List[re.Match] = []
            for pat in specific_patterns:
                matches.extend(list(re.finditer(pat, text, re.IGNORECASE)))

            valid_match = self._pick_best_match(text, matches)
            if not valid_match:
                continue

            start_idx = valid_match.start()

            # buffer prevents immediately ending on near-duplicate markers
            buffer = 120
            search_start = min(len(text), start_idx + buffer)

            end_idx = self._find_end_idx(text, search_start, end_patterns)
            content = text[start_idx:end_idx].strip()

            # Risk Factors in 10-Q can be short but still valid
            min_len = 200 if section_name.lower().startswith("risk") else 300
            if len(content) >= min_len:
                results[section_name] = content

        return results

    def _build_end_patterns(self, form_type: str, patterns: Dict[str, List[str]]) -> List[str]:
        # Start with all known section heading patterns for this form
        all_start_patterns: List[str] = []
        for pat_list in patterns.values():
            all_start_patterns.extend(pat_list)

        # Add common end-ish markers
        common_end = [
            r"SIGNATURES",
            r"EXHIBIT\s+INDEX",
        ]

        # Form-specific boundaries
        form_specific: List[str] = []
        if form_type == "10-Q":
            # MD&A normally ends at Item 3 or 4, or Part II
            form_specific.extend([
                r"Item\s*3[\.\-–:]",
                r"ITEM\s*3[\.\-–:]",
                r"Item\s*4[\.\-–:]",
                r"ITEM\s*4[\.\-–:]",
                r"PART\s+II",
            ])
        elif form_type == "10-K":
            form_specific.extend([
                r"Item\s*15[\.\-–:]",
                r"ITEM\s*15[\.\-–:]",
                r"PART\s+II",
                r"PART\s+III",
                r"PART\s+IV",
            ])
        elif form_type == "8-K":
            form_specific.extend([
                r"SIGNATURES",
                r"EXHIBIT\s+INDEX",
            ])
        elif form_type == "DEF 14A":
            form_specific.extend([
                r"SIGNATURES",
            ])

        # De-duplicate while preserving order
        deduped: List[str] = []
        seen = set()
        for p in (all_start_patterns + form_specific + common_end):
            if p not in seen:
                deduped.append(p)
                seen.add(p)
        return deduped

    def _find_end_idx(self, text: str, search_start: int, end_patterns: List[str]) -> int:
        end_idx = len(text)

        for end_pat in end_patterns:
            # Prefer line-start heading markers (multiline mode)
            line_pat = rf"(?m)^\s*(?:{end_pat})"
            nm = re.search(line_pat, text[search_start:], re.IGNORECASE)
            if not nm:
                nm = re.search(end_pat, text[search_start:], re.IGNORECASE)
            if nm:
                absolute_end = search_start + nm.start()
                if absolute_end < end_idx:
                    end_idx = absolute_end

        return end_idx

    def _pick_best_match(self, text: str, matches: List[re.Match]) -> Optional[re.Match]:
        if not matches:
            return None

        scored = [(self._header_score(text, m), m) for m in matches]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_match = scored[0]

        # Safe fallback: preserve old behavior if scoring can't decide
        if best_score < 0:
            return matches[-1]
        return best_match

    def _header_score(self, text: str, m: re.Match) -> int:
        """
        Score a match as a "real section header" vs TOC/cross-reference.

        Higher score = more likely a true heading.
        """
        start = m.start()
        end = m.end()

        before = text[max(0, start - 160):start]
        after = text[end:min(len(text), end + 260)]
        window = text[max(0, start - 300):min(len(text), end + 300)]

        score = 0

        # Headings usually occur at line starts (or after blank lines)
        if re.search(r"\n\s*$", before):
            score += 5
        if re.search(r"\n\s*\n\s*$", before):
            score += 3

        # TOC indicators: "Table of Contents" or dotted leaders + page numbers
        wl = window.lower()
        if "table of contents" in wl:
            score -= 8
        if re.search(r"\.{3,}\s*\d{1,4}\b", window):
            score -= 6

        # Cross-reference indicators (common failure case for CAT):
        # "...included in Part I, Item 2 of this Form 10-Q."
        combo = (before + " " + after).lower()
        if re.search(r"\bpart\s+i[, ]+\s*item\s+\d", combo):
            score -= 10
        if "of this form 10-q" in combo or "of this form 10-k" in combo:
            score -= 8
        if "see item" in combo or "refer to item" in combo:
            score -= 6

        # Penalize mid-word / mid-sentence embeddings
        if start > 0 and re.match(r"[A-Za-z0-9]", text[start - 1]):
            score -= 2

        return score