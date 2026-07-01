# Security Policy

## Supported Versions

This is a single-branch academic project — only the latest commit on `main` is supported. There are no maintained release branches.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, use [GitHub's private vulnerability reporting](https://github.com/SudeepSigdel/fyp/security/advisories/new) (Security tab → "Report a vulnerability"), or email the maintainer directly (see the [GitHub profile](https://github.com/SudeepSigdel)).

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal example helps)
- Any suggested fix, if you have one

You should get an initial response within a few days. This is a solo-maintained project, so please be patient — but genuine security issues (auth bypass, injection, secret exposure) will be prioritized over other work.

## Scope

Known, intentional limitations that are **not** considered vulnerabilities for reporting purposes:
- The ML signals are not financial advice and can be wrong — that's a product disclaimer, not a security issue (see the in-app Model Trust page and README disclaimer).
- Rate limits on `/api/auth/login` and `/api/auth/signup` are set at 10/min and 5/hour per IP respectively — this is a deliberate tradeoff, not an oversight; if you have a stronger threat model in mind, open an issue for discussion first rather than a security report.
