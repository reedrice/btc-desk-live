# BTC Desk Live — handoff

Static copy of the neon BTC desk dashboard (5m / 15m / both) served by GitHub Pages, fed live by an encrypted relay.

## How it works
- **Page:** `index.html` = `/workspace/btc5m-dashboard/index_neon.html` with the `/api/neon` fetch swapped for `liveGet()`. Animations run client-side; 5m and 15m TOTALs stay separate.
- **Relay (default): Firebase Realtime Database** `https://btc-desk-live-default-rtdb.firebaseio.com/live.json`. Rules: everything denied except public read of `/live`; writes need the legacy DB secret.
- **Pusher:** `pusher.py` every ~2.5 s builds `neon_api.build_neon('5m'|'15m')`, gzips, encrypts AES-256-GCM (PBKDF2-SHA256 200k, random salt) and PUTs `/live.json?auth=…` only when the data changed.
- **Reading:** page opens an EventSource on `/live.json` (Firebase REST streaming, `put` events) and falls back to polling every 3 s if the stream has been silent >20 s. Decrypts with WebCrypto; passphrase prompted once, kept in localStorage (`btcdesk_pw`). "data Ns old" bottom-left.
- **Gist fallback (off):** `USE_GIST=1` makes pusher write the old secret gist instead (30 s, GitHub secondary-limits after ~95 edits at 8 s). Page constant `GIST_FALLBACK` is kept but unused.
- **Box files (not in repo):** `.passphrase`, `.firebase_secret`, `.gist_id` (all chmod 600 / gitignored), `pusher.log`, `watchdog.sh`, `watchdog.pid`, `pusher.pid`.

## Limits
- Blob ~3.4 KB per update; each open device receives every update (~1.2 KB/s ≈ 3 GB/month if left open 24/7). Firebase free tier = 10 GB/month download, so ~3 always-open devices max; closed tabs cost nothing. Raise INTERVAL to cut it.
- If the box is off, the page shows the last snapshot.
- After editing index_neon.html, re-port the patch (see git history) and push to main.

## Restart
`cd /workspace/btc-desk-live && setsid nohup ./watchdog.sh >/dev/null 2>&1 < /dev/null &`

## v9 (2026-10-28) — one mascot per bot card
Old mascots were 3 blobs at hard-coded stage pixel coords (600,120 / 870,130 / 900,410), so only some cards looked "owned" and tracker/risk/your_call had none. Now `build()` docks a small bobbing blob inside each card's title bar via `MASCOT` (tracker teal, analyst pink, predictor purple, risk gold, your_call blue, pipeline orange). Lives inside the card → no overflow; works in 5m and 15m. The white carrier blob is unchanged.

## Oct 28, 2026: payload now includes `desk_total` per desk (see btc5m-dashboard/HANDOFF.md v9). Pusher restart needed only to reload neon_api.

## v10 (2026-10-28 03:20 CT) — open-position countdown
- neon_api.py adds add-only `open_positions:[{slug,side,entry,start_ts,end_ts,strategy,settle_lag_s}]`.
  5m = open candidate decisions (after settle_net netting); 15m = paper_summary.json open_slugs. Window end = slug start + 300/900s.
- UI: your_call card lists open positions with a client-side 1s ticker (`tickCD`): "closes in m:ss" until end_ts,
  then "settling… m:ss" elapsed (15m appends "(~30m)" expected lag). 'both' view shows compact rows under "open calls".
- This index.html also picked up the v9 15m desk-wide/v4 total display from the local dashboard.

## v11 (2026-10-28 ~3:30 AM CT) — plain-English open bets + README
- neon_api.py `_positions()` (add-only `open_positions` fields): cost, pays_up/pays_down, pair, exited, ptb (start price),
  now_twap/now_px (live window only), final_twap (= next window's price_to_beat), settle_lag_s (median official settle ts −
  window end from predictions.jsonl; 5m ≈ 330 s from 85 samples; 15m falls back to 1800 s until ≥5 samples), result (settled <150 s ago).
- index.html `cdRows/tickCD`: each bet reads "Bet: BTC goes UP (or ties) in the 3:15–3:20 AM CT window", payout line, target line,
  live WINNING/LOSING (or "Profit locked in" for pair locks), countdown → "waiting for official result (usually ~N min, by ~h:mm CT)"
  + provisional "Looks like a WIN/LOSS" → WON/LOST for 2 min. Compact form in "both". ⓘ legend line with tooltip.
- README.md added: what it is, how the desk works, fork-only (no PRs/contributions), secrets not included.
- Backups: index.html.bak11 (and index_neon.html.bak11 / neon_api.py.bak11 in btc5m-dashboard).
- 3:40 AM CT (v12): 15m total = v4 trades only (5m unchanged); pair-lock settlements read 'Locked pair (bought UP and DOWN) → +$X'.
- 3:50 AM CT (v13): your_call open bets are now visual tiles (▲/▼/🔒, start time, tug bar + $gap, countdown ring → ⏳~ETA, payout chip, WIN?/LOSS?, WON/LOST flash 2 min). Explanations only in the ⓘ tooltip. Backups *.bak13.
- 3:55 AM CT (v14): settling ring = static thin gray track + solid yellow arc filling by elapsed/settle_lag, '~Xm' centered, no spin/hourglass. Backups *.bak14.
- 4:10 AM CT (v15): open-bet tile grid uses minmax(0,1fr) middle col + shrinking/ellipsis payout chip + compact range '$15→$20–$41' so the ring never clips on mobile. Backups *.bak15.
- 4:17 AM CT (v16): conveyor belt moved left:196→208px and P&L tags centered on it (translateX(-50%)), carrier home 205→217px; belt+tags now share center x≈217. Backups *.bak16.

## v17 / v17b (2026-10-28 04:26 CDT)
- v17b: settling ring text = countdown to end_ts+settle_lag_s (~Nm if >=60s, m:ss under), then +m:ss overdue (removed Math.max clamp).
- v17: Polymarket-mirror chart (.pmc) per desk, client-only: ws-live-data.polymarket.com crypto_prices_chainlink btc/usd; gamma events?slug (priceToBeat, token ids, 1/window); clob midpoint every 4s. PTB fallback: gamma -> stream point at window start -> tracker.ptb. Mounted after .stage (mobile/narrow, margin-top 84px clears absolute .tot); >=1480px absolute in blank right column; cmp view after .ctot. Zero Firebase/GitHub/AI usage. Backup .bak17.

