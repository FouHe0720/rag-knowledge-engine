# Citation safety notebook

## Source path boundary
Ingest only visible relative POSIX paths under the configured corpus root. Reject absolute paths, parent traversal, backslashes, hidden path components and symlinks escaping the root. The API accepts controlled source paths and does not accept arbitrary remote URLs.

## Citation construction
The server creates citation IDs from actual selected chunks. Each citation includes source, document ID, chunk ID, page or section, normalized offsets and the exact visible supporting snippet. Model output may reference only these IDs. A resolvable citation alone does not prove the claim is entailed by its evidence.

## Insufficient evidence
When no selected passage meets the evidence threshold, return the refusal: 根据当前知识库无法确认. Show retrieval candidates and the threshold so the limitation can be inspected. A weak lexical match can still pass, so the threshold does not replace semantic verification.

## Prompt injection boundary
Retrieved documents are untrusted data, never instructions to the language model. Use a system instruction to restrict answers to evidence and validate the response schema and citation IDs. This reduces some failure modes but does not guarantee resistance to adversarial prompt injection.

## Provider credentials
Read API credentials from environment variables and exclude environment files from Git. Never include credentials or upstream response bodies in public errors. Use HTTPS for remote model providers, bounded timeouts and no automatic retries that could multiply paid requests.

## Local service boundary
The demo server binds to loopback and has no user authentication or tenant isolation. Exposing it publicly requires an authentication gateway, rate limits, parser isolation and private corpus access control. Avoid publishing private documents or provider settings in benchmark artifacts.
