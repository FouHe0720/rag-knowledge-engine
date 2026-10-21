# Environment preflight

Executed on 2026-10-21 (Asia/Shanghai client date). Parent directory verified with pwd / realpath and is not a Git repository; isolated target did not exist.

| Command | Observed result |
|---|---|
| uname -s | Linux |
| python3 --version | Python 3.12.3 |
| git --version | 2.43.0 |
| gh --version | 2.45.0 |
| gh auth status; gh api user --jq .login | authenticated as FouHe0720; no credentials recorded |
| docker --version; docker info | client/server 29.8.2 |
| node --version | v24.21.0 (not required) |
| gh repo view FouHe0720/rag-knowledge-engine | repository not found at preflight |

Commands run in Linux. No changes to global packages, proxy settings, or other projects. Machine-specific absolute paths and authentication output intentionally excluded.
