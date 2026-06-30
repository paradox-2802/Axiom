export function formatSummaryMarkdown(data) {
  if (!data) return "Could not generate an executive summary.";

  const sections = [
    ["Business Overview", data.businessOverview],
    ["Revenue & Profit", data.revenueAndProfit],
    ["Management Outlook", data.managementOutlook],
    ["Notable Changes", data.notableChanges],
  ];

  let md = "";
  for (const [title, text] of sections) {
    if (text?.trim()) {
      md += `### ${title}\n\n${text}\n\n`;
    }
  }

  if (data.keyHighlights?.length) {
    md += "### Key Highlights\n\n";
    md += data.keyHighlights.map((item) => `- ${item}`).join("\n");
    md += "\n";
  }

  return md.trim() || "No summary content could be extracted from the document.";
}

export function formatRisksMarkdown(data) {
  const risks = data?.risks || [];
  if (!risks.length) {
    return "No explicitly stated risks were found in this document.";
  }

  let md = "";
  for (const risk of risks) {
    md += `### ${risk.category} · ${risk.severity}\n\n${risk.description}\n\n`;
  }
  return md.trim();
}
