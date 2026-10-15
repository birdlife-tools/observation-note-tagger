# Release Plan: birdlife-ont-core v0.1.0

**Date:** 2026-10-15  
**Status:** COMPLETE

---

## Decisions

| # | Question | Answer |
|---|----------|--------|
| 1 | Package name | `birdlife-ont-core` |
| 2 | One package or two? | Single package (split later if needed) |
| 3 | CLI command name | `ont` (keep short) |
| 4 | Ollama-only release? | Yes — document Claude coming in v0.2 + Protocol for custom adapters |
| 5 | PyPI org status | Not approved — publish under `birdlife_tech` personal account, move to org later |
| 6 | Element token timing | Refresh before release — ensure Matrix notifications work from day 1 |

---

## Tasks (in order)

### 1. Matrix setup ✅
- [x] Refresh MATRIX_ACCESS_TOKEN (device_id: GITHUB_ACTIONS_BOT)
- [x] Get Matrix room ID: `!ZFk4tbp2YDlMj4fNKZxHvtGhZ9Vudt21JgWP2B0qJoo:matrix.org`
- [x] Update reference_matrix_notifications.md with new room ID

### 2. Package configuration ✅
- [x] Update packages/core/pyproject.toml:
  - name: `ont-core` → `birdlife-ont-core`
  - Added authors, keywords, classifiers
- [x] Add VERSION file (content: `0.1.0`)
- [x] Update README: added v0.1 note, roadmap section

### 3. Release workflow ✅
- [x] Add .github/workflows/release.yml (adapted for monorepo structure)
- [x] PYPI_API_TOKEN added to org secrets

### 4. Documentation ✅
- [x] Add "Roadmap" section to README (done in Task 2)
- [x] LLMAdapter Protocol already documented in packages/core/README.md

### 5. Release ✅
- [x] Commit all changes
- [x] Push to main (triggered release workflow)
- [x] PyPI publish succeeded: https://pypi.org/project/birdlife-ont-core/0.1.0/
- [x] Matrix notification sent (fixed room ID - no :matrix.org suffix)

### 6. Post-release ✅
- [x] Update birdlife.tech/tools page (status: released, PyPI link added)
- [x] birdlife-tools/.github README already has v0.1.0 badge (done in Task 1)
- [x] Update project memory files

---

## Secrets needed

| Secret | Scope | Status |
|--------|-------|--------|
| PYPI_API_TOKEN | repo | ? check |
| ORG_PAT | org | exists |
| MATRIX_ACCESS_TOKEN | org | refresh needed |

---

## Reference

- Release workflow pattern: `volunteer-hotspot-finder/.github/workflows/release.yml`
- Matrix room ID pattern: `!xxx:matrix.org` (get from room settings → Advanced)
- PyPI account: `birdlife_tech` (personal, until org approved)
