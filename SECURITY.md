# Security

Matters is a local-first personal intelligence system. Real user files,
messages, extracted content, identifiers, screenshots, logs, receipts,
embeddings, and derived private models must remain under an explicitly
configured `MATTERS_HOME` outside the source checkout and package build roots.

## Supported version

The private-repository 0.3.x release line is the only supported line.

## Reporting a vulnerability

Do not put private data into an issue, release, log, or reproduction fixture.
Report a vulnerability through a private channel agreed with the repository
owner and include only the minimum synthetic information needed to reproduce
the issue. The repository and releases remain private and proprietary unless a
later decision explicitly establishes a public security and license policy.

## Security boundaries

- Gmail access is read-only and requires explicit authorization.
- File discovery is restricted to declared roots and policies.
- Mailbox mutation, file deletion or execution, outbound messaging, remote
  model disclosure, and public publication are separate permissions.
- Private runtime material must never enter Git history, source archives,
  wheels, logs, screenshots, or public evidence.
- A missing or stale analysis provider is shown as unavailable or blocked; it
  must not silently fall back to a different provider.

The authoritative public/private rules are documented in
`docs/security/public-boundary.md` and `docs/security/data-classification.md`.
