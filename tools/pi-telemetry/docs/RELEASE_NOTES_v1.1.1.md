# Pi Telemetry v1.1.1

## Highlights

- Hardened source-driven update handling for local installs.
- Added explicit feed install-command support so trusted feeds can opt into auto-update.
- Kept working-tree notices prompt-only for unreleased git checkouts.
- Cleaned up version and revision histories to match the v1.1.1 release state.
- Added a concrete release-feed example payload for beta/stable distribution.

## Release Safety

- Startup checks remain read-only unless automatic update mode is enabled.
- Release-feed notices stay prompt-only without an explicit install command.
- The dashboard continues to expose the exact update command for human review.

## Documentation

- Combined OBS, AAR, and token cost analysis note: `docs/OBS_AAR_TOKEN_COST_ANALYSIS.md`
- Example feed payload: `docs/release-feed.example.json`

