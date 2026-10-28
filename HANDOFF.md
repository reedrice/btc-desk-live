# BTC Desk Live — handoff

Static copy of the neon BTC desk dashboard (5m / 15m / both) served by GitHub Pages, fed live by an encrypted relay.

## How it works
- **Page:** `index.html` = `/workspace/btc5m-dashboard/index_neon.html` with the `/api/neon` fetch swapped for `liveGet()`. Animations (conveyor belt, bot, lines) run client-side. 5m and 15m TOTALs stay separate.
- **Relay:** a secret GitHub Gist (`live.json`, reedrice). The box runs `pusher.py` every ~8 s: builds `neon_api.build_neon('5m'|'15m')`, gzips, encrypts AES-256-GCM (key = PBKDF2-SHA256, 200k iters, random salt), PATCHes the gist via `gh api`.
- **Reading:** page fetches `gist.githubusercontent.com/.../raw/live.json?t=<now>` every 3 s and keeps the newest `ts` seen (GitHub gist raw replicas lag 0–60 s independently; measured shown data ~22 s old avg, ~50 s worst), decrypts with WebCrypto. Passphrase prompted once, kept in localStorage (`btcdesk_pw`).
- **Box files (not in repo):** `/workspace/btc-desk-live/.passphrase` (600), `.gist_id`, `pusher.log`, `watchdog.sh` (restarts pusher; pids in `watchdog.pid`, `pusher.pid`).

## Limits
- Gist edits count toward GitHub content-creation limits (~500/h); 8 s ≈ 450/h. Don't lower INTERVAL.
- Data is ~20 s behind on average (up to ~50 s). If the box is off, the page shows the last snapshot (see "data Ns old", bottom-left).
- To regenerate the page after editing index_neon.html, re-run the patch step (see git history) and push to main.

## Restart
`cd /workspace/btc-desk-live && setsid nohup ./watchdog.sh >/dev/null 2>&1 < /dev/null &`
