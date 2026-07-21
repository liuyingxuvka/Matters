# Synthetic fixtures

This directory is reserved for fully synthetic, public-safe fixtures used to
exercise Matters without reading or copying a person's files, messages, or
runtime database.

Fixtures committed here must:

- describe invented people, sources, events, and identifiers only;
- contain no credentials, signed links, mailbox or provider identifiers, or
  absolute user-home paths;
- remain small enough for source review; and
- be reproducible from repository-owned scripts when generation is required.

The private first-run store, UI captures, generated runtime evidence, and
connector exports always remain outside this directory and outside release
packages.
