# GitHub Activity — 3D

An interactive Three.js visualization of GitHub contributions and commits authored by `indkhan` in repositories owned by the account.

## Live dashboard
Once GitHub Pages is enabled and the workflow completes, visit:
https://indkhan.github.io/indkhan/

## What the numbers mean
- **Contributions** are read from GitHub's contribution calendar through GraphQL.
- **Own-repo commits** count commits attributed by GitHub to `indkhan` in non-fork, non-archived repositories owned by this account. This intentionally does not claim to count commits made to other people's repositories.
- Data is refreshed daily by GitHub Actions and on every push to `main`.

## Publish it
1. Open **Settings → Pages** in this repository.
2. Set **Build and deployment → Source** to **GitHub Actions**.
3. Open **Actions** and run **Refresh 3D GitHub activity and deploy Pages** if it hasn't run automatically.
4. After a successful deployment, the dashboard is at the URL above.

No personal access token or client-side secret is needed. The workflow uses the repository's short-lived `GITHUB_TOKEN`.
