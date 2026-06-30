from typing import Any


INSIGHT_USER_PROMPTS = {
    "summary": "Generate Executive Summary",
    "risks": "Extract Risks",
}


def format_summary_markdown(data: dict[str, Any] | None) -> str:
    if not data:
        return "Could not generate an executive summary."

    sections = [
        ("Business Overview", data.get("businessOverview")),
        ("Revenue & Profit", data.get("revenueAndProfit")),
        ("Management Outlook", data.get("managementOutlook")),
        ("Notable Changes", data.get("notableChanges")),
    ]

    parts: list[str] = []
    for title, text in sections:
        if text and str(text).strip():
            parts.append(f"### {title}\n\n{text}\n")

    highlights = data.get("keyHighlights") or []
    if highlights:
        parts.append("### Key Highlights\n")
        parts.append("\n".join(f"- {item}" for item in highlights))

    return "\n".join(parts).strip() or "No summary content could be extracted from the document."


def format_risks_markdown(data: dict[str, Any] | None) -> str:
    risks = (data or {}).get("risks") or []
    if not risks:
        return "No explicitly stated risks were found in this document."

    parts: list[str] = []
    for risk in risks:
        category = risk.get("category", "Risk")
        severity = risk.get("severity", "Medium")
        description = risk.get("description", "")
        parts.append(f"### {category} · {severity}\n\n{description}\n")

    return "\n".join(parts).strip()
