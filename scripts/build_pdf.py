"""Regenerate the original, text-only two-page fixture; no third-party content."""

from pathlib import Path

from reportlab.pdfgen import canvas


def main():
    target = Path(__file__).resolve().parents[1] / "corpus" / "operations.pdf"
    pdf = canvas.Canvas(str(target), invariant=1)
    pdf.setTitle("Original RAG operations fixture")
    pdf.setAuthor("RAG Knowledge Engine contributors")
    pages = [
        [
            "Operations note: reproducible snapshots",
            "Before an evaluation, freeze the corpus manifest.",
            "The manifest records relative source names and content SHA-256 hashes.",
            "Keep query rewriting disabled for baseline comparisons.",
            "Record embedding identity, vector dimension and chunk settings.",
        ],
        [
            "Operations note: recovery checklist",
            "If an embedding provider fails during ingestion, retain the old index.",
            "A successful retry replaces the document and all vectors atomically.",
            "After deletion, verify that no orphan chunks remain searchable.",
            "Back up SQLite through its online backup API when the service is live.",
        ],
    ]
    for lines in pages:
        y = 760
        for line in lines:
            pdf.drawString(48, y, line)
            y -= 24
        pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    main()
