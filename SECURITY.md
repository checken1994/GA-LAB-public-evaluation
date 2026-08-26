# Security and Privacy

Please do not publish secrets, access tokens, cookies, private machine paths, personal data, raw runtime logs, or private archive contents in issues or pull requests. If you discover a possible secret or privacy exposure, do not quote the value; report the file path and a redacted description to the maintainer through the contact channel shown on the private GA-LAB repository.

This repository is a sanitized evaluation pack. It is not an operational service, does not accept credentials, and must not be used as a place to upload confidential benchmark data. Public artifacts may contain question text and source URLs intended for evaluation; reviewers remain responsible for respecting the terms of the cited sources.

Every publication update should run the local validation command in the README. The validator is designed to catch common accidental exposures, but it is not a substitute for human review of licensing, provenance, or Git history.
