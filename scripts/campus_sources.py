"""Check shipped excerpts and optionally verify the original DOCX paragraphs."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def check_sources(source_root: Path | None = None) -> dict:
    manifest = json.loads((ROOT / "datasets/campus/manifest.json").read_text())
    for document in manifest["documents"]:
        excerpt = ROOT / "corpus/campus" / document["file_name"]
        if hashlib.sha256(excerpt.read_bytes()).hexdigest() != document["excerpt_sha256"]:
            raise ValueError(f"Excerpt hash mismatch: {excerpt.name}")
        expected = (
            f"# {document['title']}\n\n> 山东大学（威海） · {document['year']} 年历史资料摘录。"
            "仅用于工程演示，不作为当前办事或招生依据。\n\n"
        )
        for paragraph in document["paragraphs"]:
            expected += f"## 原文第 {paragraph['index']} 段\n\n{paragraph['text']}\n\n"
        if (expected.rstrip() + "\n").encode() != excerpt.read_bytes():
            raise ValueError(f"Rebuilt excerpt mismatch: {excerpt.name}")
        if source_root is None:
            continue
        original = (source_root / document["source_path"]).resolve()
        if not original.is_relative_to(source_root.resolve()):
            raise ValueError("Source path escaped the knowledge root")
        if hashlib.sha256(original.read_bytes()).hexdigest() != document["source_sha256"]:
            raise ValueError(f"Original file changed: {original.name}")
        with zipfile.ZipFile(original) as archive:
            tree = ElementTree.fromstring(archive.read("word/document.xml"))
        paragraphs = [
            "".join(node.text or "" for node in paragraph.findall(".//w:t", NAMESPACE)).strip()
            for paragraph in tree.findall(".//w:p", NAMESPACE)
        ]
        for paragraph in document["paragraphs"]:
            if paragraphs[paragraph["index"] - 1] != paragraph["text"]:
                raise ValueError(f"Paragraph mismatch: {original.name}, {paragraph['index']}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path, help="Original local 知识库 directory (read only)"
    )
    args = parser.parse_args()
    manifest = check_sources(args.source_root)
    originals = (
        "Original files and paragraphs matched." if args.source_root else "DOCX not checked."
    )
    print(f"Verified {len(manifest['documents'])} excerpt hashes. {originals}")


if __name__ == "__main__":
    main()
