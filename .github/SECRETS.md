# GitHub Actions Secrets

## Required Secrets

Configure these at: https://github.com/rnh735edith/homeGallery/settings/secrets/actions

### Secrets Configuration

| Secret Name | Description | Required For |
|-------------|-------------|--------------|
| `TEST_PASSWORD` | Password for test user `testadmin` | CI E2E tests |
| `JWT_SECRET` | JWT signing secret (optional - defaults to auto-generated) | CI, Production |

### How to Add Secrets

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add each secret from the table above

## Workflow Secrets Usage

### CI Workflow (`ci.yml`)

The CI workflow uses secrets for E2E test authentication:

```yaml
env:
  TEST_PASSWORD: ${{ secrets.TEST_PASSWORD }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
```

### Pages Workflow (`pages.yml`)

The Pages workflow does NOT require secrets. It uses:
- `permissions: contents: read, pages: write, id-token: write`
- Deploy environment: `github-pages`

## Secret Handling Rules

1. **NEVER hardcode secrets** in workflow files, code, or config
2. **ALWAYS use `${{ secrets.* }}`** for sensitive values
3. **NEVER log secret values** - use masking or show only placeholders
4. **Rotate secrets regularly** - especially after any potential exposure
5. **Use environment protection rules** for production deployments

## Current Status

- ✅ Pages workflow: No secrets required (uses built-in permissions)
- ✅ CI workflow: Can run without secrets (uses default test credentials)
- ⚠️ Recommended: Add `TEST_PASSWORD` secret for E2E test isolation
