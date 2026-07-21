"""Invoke the shared Matters CLI; this skill owns no alternate business path."""

from matters.cli.main import main

raise SystemExit(main())
