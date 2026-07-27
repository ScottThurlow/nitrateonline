# Project instructions

Static archive site on **Cloudflare Pages**. No build step — the repository root is served
as-is (URL rewrites/legacy redirects live in `_redirects`).

## Branch & release workflow — STRICT

**`main` is the single source of truth. The deploy branches `ppe` (staging) and `prod`
(production) only ever move *forward to match* `main` — never the reverse.**

1. **All work lands on `main` first** (open a PR into `main`).
2. **Never commit to `ppe` or `prod`. Never push a feature/work branch to them.** They are
   updated **only** by pulling from `main`.
3. **Release path is `main` → `ppe` → `prod`, each a fast-forward** from `main`:
   ```sh
   git switch main && git pull --ff-only
   git switch ppe  && git merge --ff-only main && git push   # staging
   git switch prod && git merge --ff-only main && git push   # production (Cloudflare Pages)
   ```
   Both `ppe` and `prod` fast-forward from **`main`** (not from each other).
4. **If `git merge --ff-only main` fails,** that deploy branch has diverged (something was
   committed to it directly). Do **NOT** `--force` blindly — reconcile by merging the deploy
   branch **into** `main` first (recover the stray work), verify, push `main`, then fast-forward.

`main` is PR-protected on GitHub. Releases to `ppe`/`prod` never open a PR — they only fast-forward.
