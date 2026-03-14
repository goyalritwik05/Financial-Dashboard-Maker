# Security Policy

## Supported Versions
Security fixes are applied to the latest main branch.

## Reporting a Vulnerability
Please do not create a public issue for security problems.

Report privately with:
- vulnerability summary,
- impact,
- reproduction steps,
- suggested mitigation.

The maintainer will acknowledge within 72 hours and provide a remediation plan.

## Secure Development Notes
- File input validation is required for uploaded statements.
- SQL writes must use parameterized statements.
- Avoid storing sensitive raw account data in logs.
