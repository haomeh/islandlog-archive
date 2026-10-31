# newsfetch deploy files (R90, T79)

These files are a proposal. Nothing here is installed. Install needs the user's approval (task T80, R346.4).
The service runs `python3 -m tools.newsfetch.daily`. Read `../WORKFLOW.md` for the steps, the alerts and the recovery.

| File | Use |
|---|---|
| `islandlog-newsfetch.service` | The daily layer. `Type=oneshot`, `TimeoutStartSec=12h`, sandbox on, writes only below `~/islandlog-news`. |
| `islandlog-newsfetch.timer` | 04:30 Asia/Taipei, `Persistent=true`, up to 15 min random delay. |
| `islandlog-newsfetch-fresh.service` and `.timer` | `daily.py --check-freshness` every 6 hours. It writes `ALERT` when the newest report is older than 26 hours. |
| `newsfetch.env.example` | Example of `~/.config/islandlog-newsfetch.env`. |

## Install (after approval)

1. Copy `newsfetch.env.example` to `~/.config/islandlog-newsfetch.env`. Set `ISLANDLOG_ARCHIVE_REPO` to the archive clone and set the `PATH=` line to the real tool paths of the host. The clone needs `tools/newsfetch/node_modules` and the Playwright browser.
2. Run `mkdir -p ~/islandlog-news/corpus`. The unit fails to start when `~/islandlog-news` does not exist (`ReadWritePaths`). The PM then copies `data/all7.jsonl` to `~/islandlog-news/corpus/corpus.jsonl` once (R346.3).
3. Run `loginctl enable-linger "$USER"`. Without it, the user manager and both timers stop when the user logs out.
4. Make the sandbox paths right. `ReadWritePaths=%h/islandlog-news` is fixed in the unit.
   - If you set `NEWSFETCH_DATA_DIR` to another folder, add that folder to `ReadWritePaths`. The run cannot write there otherwise.
   - The fetch step (R347.2) writes refs in the clone. Add `<clone>/.git` to `ReadWritePaths`.
   - Use a drop-in: `systemctl --user edit islandlog-newsfetch.service`, then write `[Service]` and `ReadWritePaths=` lines. Do the same for the freshness service only if its data folder changes.
5. Copy the four unit files to `~/.config/systemd/user/`.
6. Run `systemd-analyze --user verify ~/.config/systemd/user/islandlog-newsfetch*.{service,timer}`.
7. Run `systemctl --user daemon-reload`.
8. Run `systemctl --user enable --now islandlog-newsfetch.timer islandlog-newsfetch-fresh.timer`.
9. Check with `systemctl --user list-timers` and `journalctl --user -u islandlog-newsfetch`.

## Rules in the code

- The daily layer never changes files in the repo tree (no commit, push, branch, checkout or file change). Its only write is `git fetch origin main`, which moves the refs in `.git` and nothing else (R347.2). A fetch failure fails the run before the crawl.
- It keeps 1 request per 1.1 s per host (`MIN_HOST_GAP`). A host gap under 1099 ms fails the crawl step.
- The corpus changes only after merge and clustering succeed. The merge writes a temp file and renames it.
- A validator that is not set (`BLOCKED`) gives an alert (R347.3). A LAN snapshot that differs from `origin/main` for more than 24 hours gives an alert (R347.4).
- A signal stops the child process groups. `systemd` stops the whole cgroup on `stop` and on timeout.
