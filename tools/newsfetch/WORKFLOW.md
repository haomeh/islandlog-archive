# 新聞管線工作流程（T79，R346）

本文件分兩層。每日層自動執行，不改公開內容。發布層由人工派工，每一步要通過雙重確認（R336）。
程式在 `tools/newsfetch/daily.py` 和 `tools/newsfetch/merge_corpus.py`。部署檔在 `tools/newsfetch/deploy/`。

## 1. 每日層（自動）

資料夾 `~/islandlog-news`（可用 `NEWSFETCH_DATA_DIR` 改）：

| 路徑 | 內容 |
|---|---|
| `corpus/corpus.jsonl` | 新聞語料。第一次由 PM 指派複製 `data/all7.jsonl` 當種子（R346.3）。 |
| `state.json` | `last_good_date` 和各媒體連續零列次數。 |
| `reports/DATE.json`、`DATE.md` | 每日報告。保留最近 14 天。 |
| `runs/DATE/` | 當天工作資料夾（爬取輸出、日誌、`clusters-ng.json`、`dry/`）。下次執行時刪除。 |
| `ALERT` | 警報檔。有警報才存在。 |
| `daily.lock` | 鎖檔。 |

每日層按順序執行下列步驟。每一步在報告中記錄開始、結束、計數和 rc。

1. `lock`：取得 `daily.lock`。如果另一次執行持有鎖，本次以 rc 75 結束，不寫任何檔案，也不寫 `ALERT`。
2. `fetch`：在 repo 複本執行 `git fetch origin main`（R347.2）。這一步只更新 `.git` 裡的 ref，不寫 `FETCH_HEAD`，不動工作樹。失敗就是步驟失敗，後面的步驟全部跳過，語料不變。
3. `crawl`：從 `last_good_date`（沒有就用語料最新日期）爬到今天（臺北日期）。每個主機一個程序。`ltn`、`ettoday`、`newtalk` 走 `auto` 路線，其他媒體走 `click` 路線（R179）。每個程序都設定 `NEWSFETCH_REQUEST_LOG` 和 `--no-resume`。
   - 如果任何主機的最小請求間隔低於 1099 ms，本步驟失敗（R61、R175）。
   - 報告列出各主機最小間隔、防護拒絕次數和 robots 中止次數（R192）。
4. `merge`：`merge_corpus` 把新列合併到暫存檔 `runs/DATE/corpus.next.jsonl`。每個正規化網址只留一列。舊列逐位元相同。語料本身不變。
5. `cluster`：用 `PYTHONHASHSEED=0` 執行 `cluster.py --as-news-groups`，輸出 `runs/DATE/clusters-ng.json`（R149）。
6. `promote`：前面五步都成功，才把暫存檔改名成語料，並更新 `state.json`。前面任何一步失敗，語料和 `state.json` 都不變。
7. `dry_run`：把 `origin/main` 用 `git archive` 匯出到 `runs/DATE/dry/`，在那裡執行 `topics_full`，`--today` 設成臺北日期。這一步約 55 分鐘。
8. `validate`：如果有驗證器執行檔（`NEWSFETCH_VALIDATOR`，或 PATH 上的 `islandlog`），或有 `NEWSFETCH_SERVER_REPO` 加 `go`，就對 `dry/` 執行 `validate --mode full`。兩者都沒有就標示 `BLOCKED`。`BLOCKED` 會產生警報（R347.3）。T80 要設定驗證器。
9. `report`：寫 `reports/DATE.json` 和 `.md`（繁體中文），再寫或刪除 `ALERT`。

之後清理：刪除 `runs/` 下其他日期的資料夾，只保留最近 14 天的報告。語料不刪。

每日層不寫入 repo 工作樹：不 commit、不 push、不建分支、不改 `events/`、`sources/` 和狀態檔。它用 `git archive`、`git rev-parse`、`git status` 和 `git fetch origin main`。`git fetch` 只更新 `.git` 裡的 ref（R347.2）。因此 `origin/main` 是當次 `fetch` 取得的版本。

`crawl` 和 `cluster` 讀工作樹（checkout）裡的程式。`dry_run` 讀 `origin/main` 的內容。兩者可能不是同一個 commit。報告同時列出 `origin/main` 和工作樹 HEAD。

限制：只提供最新文章的媒體，漏跑的日子補不回來。程式不偵測這種缺口。

報告內容：各媒體新增列數、零列媒體、防護拒絕、robots 中止、新主題、re-gate 計數、`withdraw_blocked` 與原因、補寫候選、LAN API 的 `archive_commit` 對 `origin/main`、磁碟用量。

補寫候選是給人看的清單：最大的群集，含最近 3 天的列，而且沒有已發布事件，附媒體家數。「已發布」的判斷用網址：已發布事件引用的來源檔 `sources/*/ID.yaml` 的 `url`，與群集成員的正規化網址比對。清單不寫入任何檔案。

## 2. 發布層（人工派工）

發布層由 PM 派工。每個 repo 同時只有一個寫入 agent。

1. 讀最新的每日報告。如果 `ALERT` 存在，先處理警報（第 3 節）。如果 `validate` 步驟是 `BLOCKED`，不要發布：在分支上自己執行 `islandlog validate --mode full .`（或在 `server/` 用 `go run . validate --mode full <分支路徑>`），通過後才繼續。
2. 把當天的 `corpus.jsonl` 和 `runs/DATE/clusters-ng.json` 複製到 PM 的資料夾。記錄兩個檔案的 sha256。報告裡的 `origin/main` commit 要等於分支的起點。
3. 在新分支上做真實的 `topics_full`（R150）：
   `PYTHONHASHSEED=0 python3 -m tools.newsfetch.topics_full CORPUS CLUSTERS tools/newsfetch/topic_seeds.json . REPORT --today <臺北日期>`
   - 只暫存有改動的 `events/`、`actors/`、`sources/`、`corrections/` 和 `topic_state.json`，逐一指名，不用 `git commit -a`（R189.5）。
   - 結果要等於當天的 dry run（R190.3）。不要用假日期（R150）。
4. 精準度回合（R165）：一個唯讀 agent 對每個新主題判斷 (a)、(b)、(c)。目標是 80%。低於 80% 時，把閘門交回寫入 agent，不合併。
5. 補寫：依補寫候選建立事件，依 PRD D36 和 CONTRIBUTING 5A。事件 id 要列入 `tools/newsfetch/enriched_topics.json`。
6. 雙重確認（R336）：兩個獨立的唯讀 verifier，用不同模型，先 sonnet 再 opus。第二個拿到證據，不拿第一個的結論。
   - 兩者不同意時，做一輪修正，再讓兩者重驗。仍不同意時，交給使用者。
7. 敏感事件（`review.sensitive: true`）一律問使用者。雙重確認不能取代這個決定。強制 push、改寫歷史和 tag 也要問使用者。
8. 撤回：`topics_full` 的安全停止規則（R133）會把超過上限的撤回寫進 `withdraw_blocked`。要撤回時，先通過第 6 步，再用 `--approve-withdraw FILE` 列出 id（R221）。
9. 合併和 push：先問使用者。agent 不 push。
10. 在 `server/` 執行 `make archive-clone`，更新 LAN 快照。下一份每日報告的 LAN API 一欄要顯示「相同」。

## 3. 警報

`ALERT` 的第一行是時間，後面每行一個原因。排除原因後，下一次成功的每日執行會自動刪除 `ALERT`。

| 原因文字 | 意義 | 處理 |
|---|---|---|
| `step X failed: ...` | 步驟 X 失敗。語料不變（`dry_run` 之後的失敗除外，見第 4 節）。`crawl rc {...}` 只表示某個爬取程序失敗，不是 R61 違規。 | 讀 `runs/DATE/logs/` 和 `runs/DATE/*.out`。修好後重跑。 |
| `crawl` 且訊息含 `hosts under 1099 ms` | 某主機請求間隔不夠。這是 R61 違規。 | 停止爬取。找出原因。交給 PM。不要用較短的間隔重跑。 |
| `step validate BLOCKED: ...` | 沒有設定驗證器，dry run 沒有驗證（R347.3）。 | 設定 `NEWSFETCH_VALIDATOR` 或 `NEWSFETCH_SERVER_REPO`（T80）。發布前在分支上自己執行驗證器。 |
| `LAN snapshot is stale: ...` | LAN API 的 `archive_commit` 和 `origin/main` 不同，已超過 24 小時（R347.4）。 | 在 `server/` 執行 `make archive-clone`（第 2 節第 10 步）。 |
| `outlet X had 0 new rows in N runs` | 媒體 X 連續兩次（含）沒有新列。 | 檢查該媒體的路線是否壞了（版面改變、robots 擋住、防護拒絕）。派工修路線。 |
| `new rows N are under the floor F` | 新列總數低於下限 `NEWSFETCH_MIN_NEW_ROWS`（預設 300）。 | 看各媒體新增列數。如果多數媒體是零，查網路或路線。 |
| `stale: the newest report ... is N hours old` | 最新報告超過 26 小時。計時器沒跑，或執行卡住。 | 用 `systemctl --user status` 和 `ps` 檢查。不要用名稱殺程序（R102）。 |

新鮮度檢查是 `python3 -m tools.newsfetch.daily --check-freshness`。計時器 `islandlog-newsfetch-fresh.timer` 每 6 小時執行一次。

## 4. 中斷後復原

1. 用 `ps` 確認前一次執行已結束（R189.2）。鎖檔在程序結束時自動釋放，不必手動刪除。
   - 手動執行被 SIGKILL 或當機中斷時，爬取的 child 程序可能還活著。程式用 `PR_SET_PDEATHSIG` 盡量讓 child 跟著結束，但 child 底下的瀏覽器程序不一定結束。
   - 重跑前，先停止這次執行的 child PID（用 `ps -o pid,ppid,pgid,cmd` 找出 `tools.newsfetch.backfill` 的 PID，逐一用 PID 停止，不用名稱，R102）。否則同一主機會有兩個程序同時請求（R61 風險）。
   - 收到 SIGTERM、SIGINT 或 SIGHUP 時，程式會停止所有 child 的程序群組後結束。在 systemd 下，cgroup 會一起停止。
2. 看 `ALERT` 和最新報告，找出最後完成的步驟。
3. 如果中斷發生在 `promote` 之前：語料和 `state.json` 沒變。直接重跑 `python3 -m tools.newsfetch.daily`。同一天重跑會清掉 `runs/DATE/` 重來。
4. 如果中斷發生在 `promote` 之後（`dry_run` 或 `validate` 失敗）：語料已含當天新列，`last_good_date` 已前進。重跑會得到很少的新列，所以可能出現「under the floor」警報。這是已知現象。dry run 的結果以重跑為準。下一次完整的每日執行會清除警報。
5. 如果語料有疑慮：比對 `reports/` 中 `merge` 步驟的 sha256。語料是追加式檔案：舊列逐位元不變，可以用舊檔當前綴比對。
6. 重跑後確認 `reports/DATE.json` 的 `status` 是 `ok`，而且 `ALERT` 已不存在。

## 5. 安裝

計時器的安裝是 T80（需要使用者同意，並先在 systemd 沙盒和 Chromium 下實測，R315.3）。步驟在 `deploy/README.md`。

安裝要注意：`PATH=` 要寫進環境檔；要執行 `loginctl enable-linger`；要先 `mkdir -p ~/islandlog-news/corpus`；沙盒要能寫資料夾和 repo 複本的 `.git`（`fetch` 步驟）。服務的 `TimeoutStartSec=12h`，高於各步驟逾時的總和。
