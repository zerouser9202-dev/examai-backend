"""
MCQ Extraction Engine
Hybrid approach: Regex pattern matching + AI reconstruction
Handles broken questions, multi-column layouts, merged lines.
"""
import re
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedQuestion:
    question_number: int
    question_text: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: Optional[str] = None
    source_page: Optional[int] = None
    confidence_score: float = 1.0
    needs_review: bool = False
    review_reason: Optional[str] = None

    def to_dict(self):
        return {
            "question_no": self.question_number,
            "question": self.question_text,
            "options": {
                "A": self.option_a or "",
                "B": self.option_b or "",
                "C": self.option_c or "",
                "D": self.option_d or "",
            },
            "correct_answer": self.correct_answer,
            "needs_review": self.needs_review,
            "confidence_score": self.confidence_score,
        }


class MCQRegexExtractor:
    """
    Regex-based MCQ extraction from cleaned OCR text.
    Handles multiple question numbering and option formats.
    """

    # Question number patterns
    Q_PATTERNS = [
        r"(?:^|\n)\s*Q\.?\s*(\d+)[.:\)]\s*",        # Q1. Q1: Q1)
        r"(?:^|\n)\s*Question\s+(\d+)[.:\)]\s*",      # Question 1.
        r"(?:^|\n)\s*(\d+)[.:\)]\s+(?=[A-Z\(])",      # 1. 1) 1:
        r"(?:^|\n)\s*\((\d+)\)\s*",                    # (1)
        r"(?:^|\n)\s*[①②③④⑤⑥⑦⑧⑨⑩]",             # Unicode circled numbers
    ]

    # Option patterns - comprehensive coverage
    OPT_PATTERNS = [
        # Standard: A) B) C) D) or A. B. C. D.
        r"(?:^|\n)\s*\(?([ABCDabcd])\s*[.):\-]\s*(.+?)(?=\n\s*\(?[ABCDabcd]\s*[.):\-]|\n\s*(?:Q\.?\s*)?\d+[.:\)]|$)",
        # (a) (b) (c) (d)
        r"(?:^|\n)\s*\(([ABCDabcd])\)\s*(.+?)(?=\n\s*\([ABCDabcd]\)|\n\s*\d+[.:\)]|$)",
    ]

    # Answer key patterns
    ANSWER_PATTERNS = [
        r"(?:^|\n)\s*(\d+)\s*[.:\)→>\-]\s*\(?([ABCDabcd])\)?",
        r"(?:Ans|Answer|Key)\s*[.:\-]?\s*\(?([ABCDabcd])\)?",
        r"(?:^|\n)\s*(\d+)\s*\.\s*([ABCDabcd])\b",
    ]

    def extract(self, text: str, page_number: int = 1) -> list[ExtractedQuestion]:
        """Extract MCQs from OCR text using regex patterns."""
        text = self._normalize_text(text)
        questions = self._parse_questions(text, page_number)
        return questions

    def _normalize_text(self, text: str) -> str:
        """Clean and normalize OCR text before parsing."""
        # Fix common OCR mistakes
        replacements = {
            "0ption": "Option",
            "optlon": "option",
            "Whlch": "Which",
            "ls ": "is ",
            " lf ": " if ",
            "|": "I",  # OCR pipe → capital I
            "l)": "1)",  # OCR l → 1 in numbering
        }
        for wrong, right in replacements.items():
            text = text.replace(wrong, right)

        # Normalize whitespace but preserve newlines
        lines = [line.rstrip() for line in text.split("\n")]
        # Merge hyphenated line breaks
        merged = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.endswith("-") and i + 1 < len(lines):
                line = line[:-1] + lines[i + 1]
                i += 2
            else:
                merged.append(line)
                i += 1
        return "\n".join(merged)

    def _parse_questions(self, text: str, page_number: int) -> list[ExtractedQuestion]:
        """Split text into question blocks and parse each."""
        # Find all question start positions
        q_start_pattern = re.compile(
            r"(?:^|\n)(?:\s*)(?:Q\.?\s*)?(\d+)[.:\)]\s",
            re.MULTILINE | re.IGNORECASE
        )

        matches = list(q_start_pattern.finditer(text))
        if not matches:
            return []

        questions = []
        for idx, match in enumerate(matches):
            q_num = int(match.group(1))
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            block = text[start:end].strip()

            question = self._parse_question_block(block, q_num, page_number)
            if question:
                questions.append(question)

        return questions

    def _parse_question_block(
        self, block: str, q_num: int, page_number: int
    ) -> Optional[ExtractedQuestion]:
        """Parse a single question block into ExtractedQuestion."""

        # Option split patterns
        opt_pattern = re.compile(
            r"\n\s*\(?([ABCDabcd])\s*[.):\-]\s*",
            re.IGNORECASE
        )

        parts = opt_pattern.split(block)

        if len(parts) < 2:
            # Can't find options - needs AI review
            return ExtractedQuestion(
                question_number=q_num,
                question_text=block.strip(),
                source_page=page_number,
                confidence_score=0.3,
                needs_review=True,
                review_reason="Could not detect answer options",
            )

        # First part is question text (strip the question number prefix)
        q_text = re.sub(r"^(?:Q\.?\s*)?(\d+)[.:\)]\s*", "", parts[0], flags=re.IGNORECASE).strip()

        options = {}
        i = 1
        while i < len(parts) - 1:
            label = parts[i].upper()
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            # Clean trailing newlines and next-question leakage
            content = content.split("\n")[0].strip()
            if label in ("A", "B", "C", "D"):
                options[label] = content
            i += 2

        # Check for detected correct answer in block (e.g., "Ans: B" or "* B")
        correct = self._detect_inline_answer(block)

        q = ExtractedQuestion(
            question_number=q_num,
            question_text=q_text,
            option_a=options.get("A"),
            option_b=options.get("B"),
            option_c=options.get("C"),
            option_d=options.get("D"),
            correct_answer=correct,
            source_page=page_number,
            confidence_score=self._score_confidence(q_text, options),
        )

        # Validate
        if not q_text or len(q_text) < 5:
            q.needs_review = True
            q.review_reason = "Question text too short or missing"
        elif len(options) < 2:
            q.needs_review = True
            q.review_reason = f"Only {len(options)} options detected (expected 4)"

        return q

    def _detect_inline_answer(self, text: str) -> Optional[str]:
        """Detect answer within question block."""
        patterns = [
            r"(?:Ans|Answer|Correct)\s*[.:\-]?\s*\(?([ABCDabcd])\)?",
            r"\*\s*\(?([ABCDabcd])\)?",  # Marked with asterisk
            r"\[([ABCDabcd])\]",          # [B]
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).upper()
        return None

    def _score_confidence(self, q_text: str, options: dict) -> float:
        """Score extraction confidence 0-1."""
        score = 1.0
        if len(q_text) < 10:
            score -= 0.3
        if len(options) < 4:
            score -= 0.1 * (4 - len(options))
        if q_text.count("?") == 0 and len(q_text) < 30:
            score -= 0.1
        return max(0.0, round(score, 2))

    def extract_answer_key(self, text: str) -> dict[str, str]:
        """Extract standalone answer key (e.g., 1→B, 2→A...)."""
        pattern = re.compile(
            r"(\d+)\s*[.:\)→>\-]\s*\(?([ABCDabcd])\)?",
            re.MULTILINE
        )
        answers = {}
        for match in pattern.finditer(text):
            q_num = match.group(1)
            answer = match.group(2).upper()
            answers[q_num] = answer
        return answers


class AnswerKeyDetector:
    """
    Detect and extract answer keys from OCR text.
    Handles tabular answer keys, inline answers, appendix sections.
    """

    SECTION_HEADERS = [
        "answer key", "answers", "correct answers", "solutions",
        "answer sheet", "key", "उत्तर"  # Hindi: answers
    ]

    def find_answer_section(self, text: str) -> Optional[str]:
        """Find the answer key section in full document text."""
        lines = text.lower().split("\n")
        for i, line in enumerate(lines):
            for header in self.SECTION_HEADERS:
                if header in line:
                    # Return text from this line onwards
                    return "\n".join(text.split("\n")[i:])
        return None

    def extract_from_document(self, full_text: str) -> dict[str, str]:
        """Extract answer key from complete document text."""
        extractor = MCQRegexExtractor()

        # Try to find dedicated answer section
        answer_section = self.find_answer_section(full_text)
        if answer_section:
            answers = extractor.extract_answer_key(answer_section)
            if answers:
                logger.info(f"Found answer key section with {len(answers)} answers")
                return answers

        # Fall back to inline answer detection in full text
        answers = extractor.extract_answer_key(full_text)
        logger.info(f"Extracted {len(answers)} inline answers")
        return answers
