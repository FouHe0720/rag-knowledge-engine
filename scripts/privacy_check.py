"""Review tracked/staged candidates without printing suspected secret values."""

import re
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True
    ).splitlines()
    patterns = {
        "credential": re.compile(
            r"(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,})"
        ),
        "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "machine_path": re.compile(r"/(?:home)/[^/\s]+/|/mnt/[a-z]/|[A-Z]:\\Users\\"),
    }
    findings = []
    forbidden = {".venv", "data", "private", "models", "downloads", "__pycache__"}
    for name in sorted(set(names)):
        path = root / name
        if not path.is_file():
            continue
        if any(part in forbidden for part in path.parts) or (
            path.name.startswith(".env") and path.name != ".env.example"
        ):
            findings.append((name, "forbidden_file"))
        raw = path.read_bytes()
        if path.suffix == ".pdf":
            # Original fixture; manually review its metadata/text in ingestion tests.
            continue
        content = raw.decode("utf-8", errors="replace")
        for label, pattern in patterns.items():
            if pattern.search(content):
                findings.append((name, label))
    if findings:
        for name, label in findings:
            print(f"REVIEW REQUIRED: {name}: {label}")
        raise SystemExit(1)
    print(
        f"Privacy pattern scan passed: {len(set(names))} candidate files. "
        "Manual provenance/domain review still required."
    )


if __name__ == "__main__":
    main()
