# newsfetch deploy files (R90)

These files are a proposal. Nothing here is installed. Install needs the user's approval.

1. Edit `WorkingDirectory`, `--out-dir` and `--log-dir` in `islandlog-newsfetch.service`.
2. Copy both files to `~/.config/systemd/user/`.
3. Run `systemctl --user daemon-reload`.
4. Run `systemctl --user enable --now islandlog-newsfetch.timer`.
5. Check with `systemctl --user list-timers` and the log files in the log folder.

The daily run reads the last 3 days of every outlet in `feeds.json`. It keeps 1 request per second per host.
Outlets with status `blocked` are skipped. Outlets with status `latest_only` give only their newest items, so a daily run is the only way to grow their reach.
