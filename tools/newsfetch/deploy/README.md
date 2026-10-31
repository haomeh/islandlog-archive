# newsfetch deploy files (R90, T79)

These files are a proposal. Nothing here is installed. Install needs the user's approval (task T80, R346.4).
The service runs `python3 -m tools.newsfetch.daily`. Read `../WORKFLOW.md` for the steps, the alerts and the recovery.

| File | Use |
|---|---|
| `islandlog-newsfetch.service` | The daily layer. `Type=oneshot`, `TimeoutStartSec=6h`, sandbox on, writes only below `~/islandlog-news`. |
| `islandlog-newsfetch.timer` | 04:30 Asia/Taipei, `Persistent=true`, up to 15 min random delay. |
| `islandlog-newsfetch-fresh.service` and `.timer` | `daily.py --check-freshness` every 6 hours. It writes `ALERT` when the newest report is older than 26 hours. |
| `newsfetch.env.example` | Example of `~/.config/islandlog-newsfetch.env`. |

## Install (after approval)

1. Copy `newsfetch.env.example` to `~/.config/islandlog-newsfetch.env`. Set `ISLANDLOG_ARCHIVE_REPO` to the archive clone. The clone needs `tools/newsfetch/node_modules` and the Playwright browser.
2. Make `~/islandlog-news/corpus/corpus.jsonl`. The PM copies `data/all7.jsonl` there once (R346.3).
3. Copy the four unit files to `~/.config/systemd/user/`.
4. Run `systemd-analyze --user verify ~/.config/systemd/user/islandlog-newsfetch*.{service,timer}`.
5. Run `systemctl --user daemon-reload`.
6. Run `systemctl --user enable --now islandlog-newsfetch.timer islandlog-newsfetch-fresh.timer`.
7. Check with `systemctl --user list-timers` and `journalctl --user -u islandlog-newsfetch`.

## Rules in the code

- The daily layer never writes to the repo tree (no commit, push, branch, or file change). `ProtectSystem=strict` enforces this for the unit.
- It keeps 1 request per second per host. A host gap under 1099 ms fails the crawl step.
- The corpus changes only after merge and clustering succeed. The merge writes a temp file and renames it.
