"""
Output guardrails — PII redaction, SQL safety, hallucination warnings.
"""

import re


PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
}

DANGEROUS_SQL = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class OutputGuard:
    def sanitize(self, response: str) -> str:
        response = self._redact_pii(response)
        return response

    def _redact_pii(self, text: str) -> str:
        for pii_type, pattern in PII_PATTERNS.items():
            text = pattern.sub(f"[REDACTED-{pii_type.upper()}]", text)
        return text

    @staticmethod
    def validate_sql(sql: str) -> tuple[bool, str]:
        stripped = sql.strip().rstrip(";").strip()

        if not stripped.upper().startswith("SELECT"):
            return False, "Only SELECT statements are allowed."

        if DANGEROUS_SQL.search(stripped):
            return False, "SQL contains disallowed keywords (DROP/DELETE/UPDATE/INSERT/etc.)."

        if ";" in stripped:
            return False, "Multiple statements are not allowed."

        return True, ""

    @staticmethod
    def add_low_relevance_warning(response: str) -> str:
        return (
            "**Note:** Limited information available on this topic. "
            "The following answer is based on the closest matching documents "
            "and may not fully address your question.\n\n" + response
        )
