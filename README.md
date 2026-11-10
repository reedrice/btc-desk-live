# BTC Desk Live

A personal, paper-money dashboard for a small team of AI bots that make practice trades on
Polymarket's **"Bitcoin Up or Down"** markets. This is Reed's own project. It is shared with a few
friends to look at, not offered to the public.

## Repository scope

This is the **dashboard and encrypted relay**, not a complete bot desk or a backup of the running
system. The repo contains `index.html`, the read-only payload builder `neon_api.py`,
`pusher.py`, and `watchdog.sh`. Tracker, Analyst, Predictor, Risk, and Orchestrator implementations,
their operating rules, and their live data are maintained separately.

A matching dashboard file does not establish that the deployed bots, payload builder, relay, or
configuration match this repo. See [HANDOFF.md](HANDOFF.md) for the source review and setup gaps.

## What you're looking at

Every 5 minutes (and, on a separate desk, every 15 minutes) Polymarket opens a market asking one
question: **will Bitcoin's price be higher at the end of this window than at the start?**

- The price comes from Chainlink, averaged over the last 60 seconds (TWAP60).
- If the end price is **equal to or higher than** the start price, **UP** wins. Ties count as UP.
- A winning share pays **$1**. You buy shares at whatever price the market charges, e.g. 84¢.
  For example, a hypothetical $14 trade at 84¢ buys about 16.7 shares, which pay $16.67 if right
  and $0 if wrong, before fees. This example is not a current position-sizing rule.

Each open trade on the dashboard says in plain words what was traded, what it pays, the start price to
beat, whether it's winning right now, and when the window closes. After a window closes the
official result takes a few minutes to post (about 5–6 minutes on 5m, about 30 minutes on 15m).
The card shows when to expect it, then shows **WON** or **LOST** for two minutes.

**Everything is paper money. No real trades are placed.**

## How the desk works

Each desk (5m and 15m) is a chain of bots, and their totals are always kept separate:

1. **Tracker** watches the market and Bitcoin price feeds and records the start price.
2. **Analyst** estimates how likely the current leader is to hold, and what the order book costs.
3. **Predictor** records paper trade or skip decisions under the desk's current rules.
4. **Risk** reports checks, pause state, and limits from the separate desk system.

An Orchestrator bot coordinates each desk. The dashboard displays their outputs; it does not
implement or enforce the trading and Risk rules. Position sizing and strategy versions can differ
by desk and reporting cohort. Current settings must be confirmed with the desk operators rather
than inferred from this README or historical examples.

## How the page gets its data

The bots write to files on a private machine. `pusher.py` packs a snapshot every few seconds,
**encrypts it** (AES-GCM, key derived from a passphrase) and uploads it to a Firebase Realtime
Database. This page (GitHub Pages) streams that blob and decrypts it in your browser after you
enter the passphrase. Without the passphrase the data is unreadable.

## Want your own? Fork it — don't contribute here

This repo stays Reed's alone. **Pull requests, issues, and contributions are not accepted.**
If a friend (or a friend's AI agent) wants to run this, **fork or copy the repo and run your own
copy**; any changes you make stay in your fork.

What you'll need to set up yourself, because **none of these secrets are in this repo**:

- **Your own bots and data** writing the desk files (`predictions.jsonl`, `current.json`,
  `analysis_current.json`, `risk_state.json`, `paper_summary.json`, heartbeats, and any optional
  panel inputs). The dashboard only reads them.
- **The missing runtime dependencies:** Python with `cryptography`, compatible `settle_net`
  and `ledger5m` modules, and the configured desk directories. Those two modules are not in this repo.
- **Reviewed deployment paths:** the pusher prepends an external dashboard directory to Python's
  import path, so a `neon_api.py` there can override the checked-in copy. The watchdog and builder
  also contain deployment-specific paths.
- **Your own passphrase** (`.passphrase`, never committed) used to encrypt the data.
- **Your own Firebase Realtime Database** with public read and secret-only writes; put its URL in
  `index.html` / `pusher.py` and its secret in `.firebase_secret` (never committed).
- **GitHub Pages** turned on for your fork.

The checked-in pusher also reads `.gist_id` at startup even when Firebase is selected.
Review and adapt the paths, dependencies, relay settings, and secret-file handling before starting
the included `watchdog.sh`. A fresh clone is not a turnkey deployment.
[HANDOFF.md](HANDOFF.md) has the technical details.

Not financial advice. It's a learning project that runs on paper money.
