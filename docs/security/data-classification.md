# Matters data classification

This table is the G0 admission boundary. A file is public only when its content,
provenance, metadata, and history all satisfy the public class.

| Class | Examples | Allowed location | Public Git |
| --- | --- | --- | --- |
| Public source | Product code, schemas, migrations, provider interfaces, i18n | `matters/` | Allowed after inventory and scan |
| Synthetic fixture | Fully invented Jira cases, people, documents, screenshots, receipts | `matters/` | Allowed after synthetic-origin review |
| Public model | OpenSpec artifacts, FlowGuard models, abstract known-good/bad cases | `matters/` | Allowed |
| Public documentation | Threat model, architecture, contributor and security docs | `matters/` | Allowed |
| Private source | Real Jira issue fields, comments, worklogs, attachments, email, chat, photos | `MATTERS_HOME` | Forbidden |
| Private derived | OCR, summaries, embeddings, indexes, thumbnails, caches, local databases | `MATTERS_HOME` | Forbidden |
| Private evidence | Real Guard receipts, coverage receipts, depth reports, logs, prompts, screenshots | `MATTERS_HOME` or Vault | Forbidden |
| Private evaluation | Explicitly selected, frozen evaluation cases and their provenance | `MATTERS_EVAL_VAULT` | Forbidden in raw form |
| Credential | Tokens, cookies, API keys, OAuth state, connector cursors | OS secret store or `MATTERS_HOME` | Forbidden |
| Stable private identifier | Real content hashes, issue keys, URLs, account IDs, local paths, hostnames | Private domains only | Forbidden |

## Classification rules

1. Renaming a real person, issue, file, or project does not make the material
   synthetic.
2. Real content hashes remain private because they can act as stable
   correlation identifiers.
3. Screenshots are private unless generated from the synthetic workspace and
   rechecked with OCR and metadata inspection.
4. A denied, unknown, partial, stale, or not-run scan cannot promote a file to
   public.
5. `.gitignore` is not the authority. Physical root separation, a tracked-file
   allowlist, history scanning, clean-clone validation, and final-package
   scanning are all required before publication.
