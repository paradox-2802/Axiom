from utils.format_insights import format_risks_markdown, format_summary_markdown


def test_format_summary_markdown():
    md = format_summary_markdown(
        {
            "businessOverview": "Acme operates globally.",
            "revenueAndProfit": "Revenue grew 10%.",
            "keyHighlights": ["Strong cash"],
            "managementOutlook": "Positive.",
            "notableChanges": "New product.",
        }
    )
    assert "Business Overview" in md
    assert "Key Highlights" in md
    assert "Strong cash" in md


def test_format_risks_markdown():
    md = format_risks_markdown(
        {
            "risks": [
                {
                    "category": "Regulatory",
                    "description": "Compliance costs may rise.",
                    "severity": "Medium",
                }
            ]
        }
    )
    assert "Regulatory" in md
    assert "Compliance costs may rise." in md
