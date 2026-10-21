"""Build and validate a disposable offline container; no model download."""

import json
import subprocess
import time
import urllib.error
from pathlib import Path

from api_smoke import request, smoke


def main():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        ["docker", "build", "-t", "rag-knowledge-engine:smoke", "."], cwd=root, check=True
    )
    cid = subprocess.check_output(
        ["docker", "run", "-d", "--rm", "-p", "127.0.0.1::8000", "rag-knowledge-engine:smoke"],
        text=True,
    ).strip()
    try:
        bindings = json.loads(subprocess.check_output(["docker", "inspect", cid], text=True))
        port = bindings[0]["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
        base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                if request(base, "GET", "/health")["status"] == "ok":
                    break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        else:
            raise RuntimeError("Container did not become healthy")
        smoke(base)
        print("Docker build and HTTP lifecycle validated.")
    finally:
        subprocess.run(["docker", "stop", cid], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
