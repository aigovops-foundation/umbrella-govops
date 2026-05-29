# Security Policy

## Reporting a Vulnerability

Email `[email protected]` with details. Do not file public issues for security reports.
We aim to acknowledge within 2 business days.

## Signing Identity

All evidence bundles produced by this repository are signed via Sigstore keyless signing,
bound to the GitHub Actions OIDC identity:

```
https://github.com/bobrapp/umbrella-govops/.github/workflows/evidence-bundle.yml@refs/heads/main
```

Verify any bundle:

```bash
cosign verify-attestation \
  --type https://aigovops.org/attestations/govops-evidence/v1 \
  --certificate-identity-regexp "https://github.com/bobrapp/umbrella-govops/.+" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  <bundle.tar.zst>
```

## Key Rotation

There are no long-lived signing keys. Identities rotate per workflow run via Fulcio
short-lived certificates (~10 minute validity) recorded in the Rekor transparency log.

## Branch Protection (required settings)

- `main` requires PR review with CODEOWNERS approval
- Required status checks: `validate-schemas`, `compile-policies`, `run-checks`, `gate`
- Linear history required
- Force-push and deletion disabled
