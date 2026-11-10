# BTC Desk Live handoff

Static BTC desk dashboard (5m / 15m / both), plus a read-only payload builder and encrypted relay.

## Source review: 2026-11-10

Reviewed source baseline: [`16a7821` (2026-11-04)](https://github.com/reedrice/btc-desk-live/commit/16a7821cd0fac802295da8fda6da44e5ea568b09).
This review describes committed code, not current process health or deployed strategy settings.

- **Included:** `index.html`, `neon_api.py`, `pusher.py`, `watchdog.sh`, and documentation.
- **Outside this repo:** the bots and their rules, live desk files, credentials, settlement/ledger
  dependencies, and the complete deployment environment. This repo is not a full desk backup.
- **Historical UI comparison:** a November 6 handoff reported that the installed dashboard matched
  the November 4 `index.html` (SHA-256
  `a95cb396707c1ee93417d77c94851643c79009dc8225cd5f98579f3a375f804d`).
  That is a historical single-file match, not proof that all runtime components still match.
- **Runtime drift is possible:** `pusher.py` prepends an external dashboard directory before
  importing `neon_api`. A module there can take precedence over this repo's copy. Verify the
  actual loaded module and compare each deployed file before deciding what remains to commit.
- **Payload coverage needs checking:** `index.html` has a renderer for `wallet_experiments`,
  but the checked-in `neon_api.build_neon()` does not emit that field. A deployed external builder
  may supply it; the UI source alone does not verify that integration.
- **Sizing is not fixed by this documentation:** the builder separates the 15m `bankroll_v1`
  cohort from `legacy_14` history and reads a separate 5m desk bankroll. Confirm current rules
  and reporting cohorts with each desk before updating operational claims.

## How the committed code works

- **Page:** `index.html` renders relay snapshots through `liveGet()`. The 5m and 15m totals stay
  separate. The chart also calls Polymarket's public price, market, and midpoint endpoints.
- **Relay:** Firebase Realtime Database is the default transport. The pusher PUTs an encrypted
  blob to `/live.json`; the browser receives Firebase REST streaming `put` events and checks
  every 3 seconds for a polling fallback when the stream has been silent for over 20 seconds.
  Access rules are external configuration and were not verified by this source review.
- **Payload:** the pusher builds both desks roughly every 2.5 seconds by default
  (`INTERVAL` overrides it), then gzips and encrypts the payload with AES-256-GCM.
  In Firebase mode it compares a payload hash with the last successful upload and skips equal
  hashes. Key derivation uses PBKDF2-SHA256 with 200,000 iterations and a random salt.
  A new IV is generated per encryption.
- **Browser access:** WebCrypto decrypts the blob after a passphrase prompt. The passphrase is
  stored in browser localStorage as `btcdesk_pw`; use a trusted browser profile.
- **Gist option:** `USE_GIST=1` selects pusher output to a Gist with a 30-second default interval
  and requires an authenticated `gh` CLI. The page's `GIST_FALLBACK` constant is unused, so
  changing the pusher alone does not switch the reader.
- **Watchdog:** `watchdog.sh` is tracked in this repo. It uses a lock, checks the pusher PID
  every 20 seconds, restarts it when needed, and truncates its log above roughly 2 MB.
  The script being present does not establish that it is currently running.

## Setup dependencies and limits

- Use Python 3.9+ with `cryptography` and time-zone data for `America/Chicago`.
  The Linux watchdog needs Bash, `flock`, and GNU-style `stat`.
- Supply compatible `settle_net` and `ledger5m` modules. Neither is included.
  `settle_net` is imported during every payload build; `ledger5m` supports 5m bankroll history.
- Review the hard-coded paths in the pusher, builder, and watchdog. Supply the expected desk
  JSON/JSONL files and heartbeats before launching.
- Configure your own Firebase URL and access rules. Keep `.passphrase`, `.firebase_secret`,
  and `.gist_id` out of Git. The current pusher unconditionally reads all three at startup,
  including `.gist_id` in Firebase mode and `.firebase_secret` in Gist mode.
- Serve the page over HTTPS in a browser with WebCrypto, EventSource, and
  `DecompressionStream('gzip')`. Enable GitHub Pages for your own fork if using that host.
- Start the included watchdog only after adapting and validating the deployment configuration.
  Keep credentials, desk data, logs, and runtime state private.
- Firebase download use depends on payload size, update rate, and connected clients. Measure
  actual traffic and check the provider's current quota; the original handoff's device-count estimate was
  not a capacity guarantee.
- If the publisher stops, the page can retain the last snapshot. Check freshness and source
  status separately from the fact that the page loads.

## Historical notes retained below

The following October 28 notes describe earlier work. They are not a complete changelog, current
operating instructions, proof of active services, or current strategy settings. Later changes
are recorded in Git history. No runtime or service changes were made for this documentation update.

## v9 (2026-10-28) — one mascot per bot card
Old mascots were 3 blobs at hard-coded stage pixel coords (600,120 / 870,130 / 900,410), so only some cards looked "owned" and tracker/risk/your_call had none. Now `build()` docks a small bobbing blob inside each card's title bar via `MASCOT` (tracker teal, analyst pink, predictor purple, risk gold, your_call blue, pipeline orange). Lives inside the card → no overflow; works in 5m and 15m. The white carrier blob is unchanged.

## Oct 28, 2026: payload now includes `desk_total` per desk (see btc5m-dashboard/HANDOFF.md v9). Pusher restart needed only to reload neon_api.

## v10 (2026-10-28 03:20 CT) — open-position countdown
- neon_api.py adds add-only `open_positions:[{slug,side,entry,start_ts,end_ts,strategy,settle_lag_s}]`.
  5m = open candidate decisions (after settle_net netting); 15m = paper_summary.json open_slugs. Window end = slug start + 300/900s.
- UI: your_call card lists open positions with a client-side 1s ticker (`tickCD`): "closes in m:ss" until end_ts,
  then "settling… m:ss" elapsed (15m appends "(~30m)" expected lag). 'both' view shows compact rows under "open calls".
- This index.html also picked up the v9 15m desk-wide/v4 total display from the local dashboard.

## v11 (2026-10-28 ~3:30 AM CT) — plain-English open trades + README
- neon_api.py `_positions()` (add-only `open_positions` fields): cost, pays_up/pays_down, pair, exited, ptb (start price),
  now_twap/now_px (live window only), final_twap (= next window's price_to_beat), settle_lag_s (median official settle ts −
  window end from predictions.jsonl; 5m ≈ 330 s from 85 samples; 15m falls back to 1800 s until ≥5 samples), result (settled <150 s ago).
- index.html `cdRows/tickCD`: each trade reads "Trade: BTC goes UP (or ties) in the 3:15–3:20 AM CT window", payout line, target line,
  live WINNING/LOSING (or "Profit locked in" for pair locks), countdown → "waiting for official result (usually ~N min, by ~h:mm CT)"
  + provisional "Looks like a WIN/LOSS" → WON/LOST for 2 min. Compact form in "both". ⓘ legend line with tooltip.
- README.md added: what it is, how the desk works, fork-only (no PRs/contributions), secrets not included.
- Backups: index.html.bak11 (and index_neon.html.bak11 / neon_api.py.bak11 in btc5m-dashboard).
- 3:40 AM CT (v12): 15m total = v4 trades only (5m unchanged); pair-lock settlements read 'Locked pair (bought UP and DOWN) → +$X'.
- 3:50 AM CT (v13): your_call open trades are now visual tiles (▲/▼/🔒, start time, tug bar + $gap, countdown ring → ⏳~ETA, payout chip, WIN?/LOSS?, WON/LOST flash 2 min). Explanations only in the ⓘ tooltip. Backups *.bak13.
- 3:55 AM CT (v14): settling ring = static thin gray track + solid yellow arc filling by elapsed/settle_lag, '~Xm' centered, no spin/hourglass. Backups *.bak14.
- 4:10 AM CT (v15): open-trade tile grid uses minmax(0,1fr) middle col + shrinking/ellipsis payout chip + compact range '$15→$20–$41' so the ring never clips on mobile. Backups *.bak15.
- 4:17 AM CT (v16): conveyor belt moved left:196→208px and P&L tags centered on it (translateX(-50%)), carrier home 205→217px; belt+tags now share center x≈217. Backups *.bak16.

## v17 / v17b (2026-10-28 04:26 CDT)
- v17b: settling ring text = countdown to end_ts+settle_lag_s (~Nm if >=60s, m:ss under), then +m:ss overdue (removed Math.max clamp).
- v17: Polymarket-mirror chart (.pmc) per desk, client-only: ws-live-data.polymarket.com crypto_prices_chainlink btc/usd; gamma events?slug (priceToBeat, token ids, 1/window); clob midpoint every 4s. PTB fallback: gamma -> stream point at window start -> tracker.ptb. Mounted after .stage (mobile/narrow, margin-top 84px clears absolute .tot); >=1480px absolute in blank right column; cmp view after .ctot. Zero Firebase/GitHub/AI usage. Backup .bak17.


## v18 (2026-10-28 04:32 CDT)
- neon_api adds pm={slug,ptb,src} per desk (ptb = current.json spot_open_crypto_price_feed = Polymarket open price, else price_to_beat_twap60). ~80 bytes/desk in the pusher blob.
- Chart PTB order: gamma priceToBeat -> pm.ptb (slug must match current window) -> Chainlink stream point at start -> tracker.ptb.
- Pusher + watchdog were found dead since 04:04 CDT; restarted with nohup ./watchdog.sh.
- Ladder (v16) re-verified: belt 218-236px, tag centers 226-230 at 1500 and 390 (stage layout 1140).

## v19 PAIR-LOCK (paper) panel — 2026-10-28 CT
- neon_api.build_neon("5m") adds `pairlock` (read-only from /home/box/shared/btc5m/pairlock_fast/{opportunities,paper_trades,windows}.jsonl + heartbeat_pairlock_fast.json): hb_age, paused, pnl, settled, spotted_today, filled_today, pairs, days, edge_c, naked_pct, windows_today, best_today, last[5]. 15m: null.
- UI: self-mounting `.plc` card (plDraw, 1s) — after BOT HEARTBEATS in "both" view, below the stage in 5m view. Tooltips explain each number. Empty state shows best pair cost seen today.
- Backups: *.bak19. No trading logic changed.

## v20 (Oct 28 2026) — $200 SIM cards
Two paper $200 bankroll cards (desk copy + pair-lock copy) on both desks: bankroll, sparkline, trade size, 3 streak dots, today W-L; tooltips explain. Data `/api/neon` → `sim200` from /home/box/shared/btc5m/sim200/state.json. Kept separate: never summed into desk P&L/record. Backups *.bak20.
