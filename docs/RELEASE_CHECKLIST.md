# Release Checklist

Use this checklist before publishing a GitHub release or sharing the Windows `.exe` publicly.

## Code and Tests

- [ ] Confirm the working tree only contains intended changes.
- [ ] Run backend tests: `python -m pytest -q`
- [ ] Run frontend lint: `cd frontend && npm run lint`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run a clean install on a fresh checkout or temporary folder.

## Windows EXE Smoke Test

- [ ] Build with `pyinstaller jobsmith.spec --noconfirm`.
- [ ] Start `dist/Jobsmith.exe` on Windows 10 or Windows 11.
- [ ] Confirm first launch opens the native window.
- [ ] Confirm Settings can select a local CLI backend or BYOK backend.
- [ ] Upload a small PDF resume and confirm parsing succeeds.
- [ ] Run one low-frequency job search.
- [ ] Generate one application package and confirm it appears in My Packages.
- [ ] Export a Word `.docx`.
- [ ] Open mock interview from a package.
- [ ] Use Settings to clear personal data, then confirm history/searches are removed.
- [ ] Open the error-log folder from Settings.

## Privacy and Packaging

- [ ] Remove local secrets from `.env`, logs, screenshots, and release notes.
- [ ] Do not ship local `data/`, `.pytest_cache/`, `.ruff_cache/`, or `frontend/node_modules/`.
- [ ] Include `LICENSE`, README, and privacy documentation in the release page.
- [ ] Publish a SHA-256 checksum for the `.exe`.
- [ ] State clearly whether the build is signed. Do not imply code signing if it is unsigned.

## GitHub Release

- [ ] Use a version tag, for example `v0.1.0`.
- [ ] Mention supported platforms and known limitations.
- [ ] Link to `docs/PRIVACY.md`.
- [ ] Include upgrade notes if local data paths or settings changed.
- [ ] Keep the previous release available until the new build has been smoke-tested by users.

## Public Launch

- [ ] Verify screenshots match the current UI.
- [ ] Confirm issue templates are enabled.
- [ ] Prepare a short troubleshooting note for Windows SmartScreen, missing WebView2, and missing CLI login.
- [ ] Monitor GitHub issues after launch and be ready to patch source-site breakages.
