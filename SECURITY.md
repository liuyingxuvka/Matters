# Security

Matters is a local-first personal intelligence system. Real user files,
messages, extracted content, identifiers, screenshots, logs, receipts,
embeddings, and derived private models must remain under an explicitly
configured `MATTERS_HOME` outside the source checkout and package build roots.

## Supported version

The public MIT-licensed 0.3.x release line is the only supported line.

## Reporting a vulnerability

Do not put private data into an issue, release, log, or reproduction fixture.
Open a GitHub security advisory for the repository owner and include only the
minimum synthetic information needed to reproduce the issue. Do not open a
public issue when a report contains an unpatched vulnerability, credentials, or
private data. The repository is public and open source under the MIT License;
that software license does not authorize disclosure of private user data.

## Security boundaries

- Every file-reading, information-reading, or connected-source scope requires
  explicit user authorization.
- Source-ingestion connectors are extensible but non-mutating; each connector
  is restricted to its declared authorization scope and policy.
- Mailbox mutation, file deletion or execution, outbound messaging, remote
  model disclosure, and public publication are separate permissions.
- Private runtime material must never enter Git history, source archives,
  wheels, logs, screenshots, or public evidence.
- A missing or stale analysis provider is shown as unavailable or blocked; it
  must not silently fall back to a different provider.

The authoritative public/private rules are documented in
`docs/security/public-boundary.md` and `docs/security/data-classification.md`.
