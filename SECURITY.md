# Security Policy

## Reporting a Vulnerability

Email **security@aigovops-foundation.com** with details. Do not file public issues for security reports.
We aim to acknowledge within 2 business days.

## Signing Identity

All evidence bundles produced by this repository are signed via Sigstore keyless signing,
bound to the GitHub Actions OIDC identity:

```
https://github.com/aigovops-foundation/umbrella-govops/.github/workflows/govops-ci.yml@refs/heads/main
```

Verify any bundle (or run `umbrella-conformance verify bundle.tar.gz`, which also
recomputes every digest in it):

```bash
cosign verify-blob \
  --signature bundle.tar.gz.sig \
  --certificate bundle.tar.gz.pem \
  --certificate-identity-regexp "https://github.com/aigovops-foundation/umbrella-govops/.+" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  bundle.tar.gz
```

## Key Rotation

There are no long-lived signing keys. Identities rotate per workflow run via Fulcio
short-lived certificates (~10 minute validity) recorded in the Rekor transparency log.

## Branch Protection (required settings)

- `main` requires PR review with CODEOWNERS approval
- Required status checks: `validate-schemas`, `compile-policies`, `run-checks`, `gate`
- Linear history required
- Force-push and deletion disabled
