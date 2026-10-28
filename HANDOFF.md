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
