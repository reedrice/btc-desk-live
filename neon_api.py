"""Neon night-shift dashboard API (v4). Compact, desk-parametrised state for /neon.
build_neon(desk) reads ONLY /home/box/shared/btc<desk>/ (desk in {"5m","15m"}); never writes.
Missing values stay None -> the UI renders '—'. Nothing is invented or interpolated."""
import os, json, time, calendar, math
DESKS = {"5m": "/home/box/shared/btc5m", "15m": "/home/box/shared/btc15m"}

def _rj(path):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return None
def _tail(path, n=5000):
    out = []
    try:
        with open(path, "rb") as f:
            f.seek(0, 2); s = f.tell(); f.seek(max(0, s - 2_000_000))
            for ln in f.read().decode("utf-8", "ignore").splitlines()[-n:]:
                try: out.append(json.loads(ln))
                except Exception: pass
    except OSError: pass
    return out
def _num(x):
    try:
        v = float(x); return v if math.isfinite(v) else None
    except Exception: return None
def _ts(v):
    """Heartbeats use unix floats or ISO 'Z' strings; normalise to unix seconds."""
    if v is None: return None
    n = _num(v)
    if n is not None: return n
    try: return calendar.timegm(time.strptime(str(v)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception: return None

def build_neon(desk="5m"):
    d = DESKS.get(desk, DESKS["5m"]); now = time.time(); P = lambda f: os.path.join(d, f)
    cur = _rj(P("current.json")) or {}; ac = _rj(P("analysis_current.json")) or {}
    risk = _rj(P("risk_state.json")) or {}; summ = _rj(P("paper_summary.json")) or {}
    # --- heartbeats: age in seconds; UI dims panel when age > stale_s ---
    bots = {}
    for k in ("tracker", "analyst", "predictor", "risk"):
        h = _rj(P(f"heartbeat_{k}.json")) or {}
        t = _ts(h.get("ts")) or (os.path.getmtime(P(f"heartbeat_{k}.json")) if os.path.exists(P(f"heartbeat_{k}.json")) else None)
        bots[k] = dict(agent=h.get("agent"), status=h.get("status"), activity=h.get("activity"),
                       ts=t, age=(now - t) if t else None, metrics=h.get("metrics"))
    # --- tracker: sources live vs errored (from heartbeat last_source_errors + current.errors) ---
    tm = bots["tracker"]["metrics"] or {}
    errs = dict(tm.get("last_source_errors") or {}); errs.update(cur.get("errors") or {})
    tracker = dict(chainlink=_num(cur.get("chainlink_price")), twap60=_num(cur.get("running_twap60")),
                   ptb=_num(cur.get("price_to_beat_twap60")), errored=sorted(errs),
                   live=[s for s in ("okx", "coinbase", "kraken", "bitstamp", "deribit", "chainlink") if s not in errs],
                   ws=(tm.get("ws") or {}).get("connected"), cl_age=_num(tm.get("last_chainlink_tick_age_s")),
                   slug=cur.get("slug"), seconds_remaining=_num(cur.get("seconds_remaining")),
                   start=_ts(cur.get("start_utc")), end=_ts(cur.get("end_utc")), leading=cur.get("leading_side"),
                   leading_ask=_num(cur.get("leading_ask")))
    # --- pm: current window price-to-beat for the chart (Polymarket open price, else self TWAP60) ---
    _op = _num(cur.get("spot_open_crypto_price_feed")); _tw = _num(cur.get("price_to_beat_twap60")) or _num(cur.get("self_twap60_at_start"))
    pm = dict(slug=cur.get("slug"), ptb=round(_op if _op is not None else _tw, 2) if (_op is not None or _tw is not None) else None,
              src="open" if _op is not None else ("twap60" if _tw is not None else None))
    # --- analyst: p(lead holds) = edge.p_hold if present, else derived from lean.p_up for the lean side ---
    lean = ac.get("lean") or {}; edge = ac.get("edge") or {}; pu = _num(lean.get("p_up"))
    ph = _num(edge.get("p_hold"))
    if ph is None and pu is not None and lean.get("call"): ph = pu if str(lean["call"]).lower() == "up" else 1 - pu
    analyst = dict(lean=lean.get("call"), p_hold=ph, ev=_num(edge.get("ev_per_$1")), ask=_num(edge.get("ask")),
                   in_window=(ac.get("eval_window") or {}).get("in_window"), model=ac.get("model_version"), slug=ac.get("slug"))
    # --- paper records (Predictor) ---
    recs = [r for r in _tail(P("predictions.jsonl")) if r.get("mode") == "paper"]
    dec = [r for r in recs if r.get("record") == "decision"]
    sett = [r for r in recs if r.get("record") == "settlement" and r.get("decision") == "candidate"]
    from settle_net import net_settlements; sett = net_settlements(sett)  # v5 per-leg lines -> one row per window
    settled = {r.get("slug") for r in sett}
    open_c = [dict(slug=r.get("slug"), side=r.get("side"), ask=r.get("entry_price"), ts_ct=r.get("ts_ct"),
                   ev=r.get("fee_adjusted_ev_per_dollar")) for r in dec if r.get("decision") == "candidate" and r.get("slug") not in settled]
    eq, tot = [], 0.0
    for r in sett: tot += _num(r.get("paper_pnl_after_fees")) or 0; eq.append(round(tot, 4))
    last = dec[-1] if dec else None
    pred = dict(decision=last.get("decision") if last else None, side=last.get("side") if last else None,
                ask=_num(last.get("entry_price")) if last else None, ev=_num(last.get("fee_adjusted_ev_per_dollar")) if last else None,
                reason=last.get("reasoning") if last else None, slug=last.get("slug") if last else None,
                ts_ct=last.get("ts_ct") if last else None, live=bool(last and last.get("slug") == cur.get("slug")))
    # --- run log: recent decisions + settlements (newest first) ---
    log = []; _seen = set(); _net = {x.get('slug'): x for x in sett}
    for r in recs[-40:]:
        if r.get("record") == "decision":
            log.append(dict(ts=r.get("ts"), lvl="info" if r.get("decision") == "candidate" else "dim",
                text=f"{str(r.get('decision')).upper()} {r.get('side')} @{r.get('entry_price')} · {str(r.get('reasoning') or '')[:70]}"))
        elif r.get("record") == "settlement":
            w = r.get("win"); pn = _num(r.get("paper_pnl_after_fees"))
            if "leg" in r:  # v12: 5m writes one settlement line per leg -> show one netted row per window
                if r.get("slug") in _seen: continue
                _seen.add(r.get("slug")); r = _net.get(r.get("slug"), r); w = r.get("win"); pn = _num(r.get("paper_pnl_after_fees"))
            if _is_pair(r):  # v12: pair-lock settlement: side/entry_price only reflect leg 1, so say what really happened
                log.append(dict(ts=r.get("ts"), lvl="dim" if w is None else ("ok" if (pn or 0) >= 0 else "bad"),
                    text=f"SETTLE {(r.get('slug') or '')[-10:]} → Locked pair (bought UP and DOWN) → {'' if pn is None else ('+' if pn >= 0 else '-') + '$' + format(abs(pn), '.2f')}")); continue
            log.append(dict(ts=r.get("ts"), lvl="dim" if w is None else ("ok" if w else "bad"),
                text=f"SETTLE {(r.get('slug') or '')[-10:]} → {r.get('outcome')}" + ("" if w is None else f" {'WIN' if w else 'LOSS'} {pn:+.2f}")))
    # v12: 15m desk_total counts ONLY predictor_version=='v4' (v4 began 02:15 CT; lines without the field are v3). 5m unchanged.
    # Desk-wide total from every scored settlement (all predictor versions; 15m = v3+v4). On 15m,
    # paper_summary (output.pnl) is v4-only, so both are exposed. leg/post_exit_outcome/shadow are never scored.
    _dw = []
    try:
        for _l in open(P("predictions.jsonl")):
            try: _r = json.loads(_l)
            except Exception: continue
            if _r.get("mode") == "paper" and _r.get("record") == "settlement" and _r.get("decision") == "candidate" and _r.get("win") is not None and (desk != "15m" or _r.get("predictor_version") == "v4"): _dw.append(_r)
    except Exception: pass
    _dw = net_settlements(_dw)
    desk_total = dict(wins=sum(1 for r in _dw if r.get("win")), losses=sum(1 for r in _dw if not r.get("win")),
                      pnl=round(sum(_num(r.get("paper_pnl_after_fees")) or 0 for r in _dw), 2))
    # v10: open_positions (add-only) for the client-side countdown. Window bounds come from the slug
    # (btc-updown-<5m|15m>-<start_unix>); UI ticks 'closes in' until end_ts, then 'settling' elapsed.
    # v11: plain-English open bets. Per slug: legs (main/pair/exit on 5m; record:"leg" buy/sell on 15m),
    # cost incl fees, payout if Up / if Down, start price (price to beat), live/final TWAP60, settle lag
    # (median official settlement ts - window end, measured from predictions.jsonl), and results settled <150s ago.
    W = 900 if desk == "15m" else 300
    open_positions = _positions(d, desk, W, now, cur, recs, sett, summ, open_c)
    m = risk.get("metrics") or {}; ru = risk.get("rules") or {}
    return dict(desk_total=desk_total, desk=desk, now=now, bots=bots, tracker=tracker, pm=pm, analyst=analyst, predictor=pred, open=open_c, open_positions=open_positions,
        risk=dict(status=risk.get("status"), reason=risk.get("reason"), loss_streak=m.get("current_loss_streak"),
                  max_losses=ru.get("max_consecutive_losses"), red_days=m.get("consecutive_red_days"),
                  max_red=ru.get("max_consecutive_red_days"), accuracy=m.get("accuracy")),
        output=dict(pnl=_num(summ.get("total_pnl_after_fees")), wins=summ.get("wins"), losses=summ.get("losses"),
                    fees=_num(summ.get("total_fees")), windows=summ.get("windows"), candidates=summ.get("candidates"),
                    skips=summ.get("skips"), equity=eq),
        log=log[::-1][:30], pairlock=_pairlock(d, now) if desk == "5m" else None, sim200=_sim200("/home/box/shared/btc5m" if desk == "5m" else "/home/box/shared/btc15m", now))  # v21: 15m reads its own sim200 (main account only)

# v20: sim200 — two $200 paper bankroll sims. Read-only from sim200/state.json. Kept in its OWN block:
# never added to desk_total / output / any desk record (Reed's rule).
def _sim200(d, now):
    st = _rj(os.path.join(d, "sim200", "state.json")) or {}; hb = _rj(os.path.join(d, "heartbeat_sim200.json")) or {}
    ht = _ts(hb.get("ts")); c = st.get("config") or {}
    acc = {k: dict(bankroll=v.get("bankroll"), bet=v.get("bet"), streak=v.get("green_streak"), trades=v.get("trades"),
                   today=v.get("today"), spark=v.get("spark")) for k, v in (st.get("accounts") or {}).items()}
    return dict(hb_age=round(now - ht, 1) if ht else None, start=c.get("start_bankroll"), cap=c.get("bet_cap"),
                need=c.get("green_streak_to_resize"), accounts=acc)

# v19: PAIR-LOCK (paper) summary for the 5m desk. Reads ONLY pairlock_fast/ files + its heartbeat; never writes.
def _pairlock(d, now):
    import datetime, zoneinfo
    CT = zoneinfo.ZoneInfo("America/Chicago"); pd = os.path.join(d, "pairlock_fast")
    day = datetime.datetime.fromtimestamp(now, CT).strftime("%Y-%m-%d")
    hb = _rj(os.path.join(d, "heartbeat_pairlock_fast.json")) or {}; ht = _ts(hb.get("ts"))
    opp = _tail(os.path.join(pd, "opportunities.jsonl")); tr = _tail(os.path.join(pd, "paper_trades.jsonl"))
    wins = _tail(os.path.join(pd, "windows.jsonl"))
    fills = [r for r in tr if r.get("type") == "fill"]; sets = {r.get("slug"): r for r in tr if r.get("type") == "settle"}
    tday = lambda r: str(r.get("signal_ct") or r.get("open_ct") or r.get("logged_ct") or "")[:10] == day
    att = [f for f in fills if f.get("legs")]; pairs = [f for f in att if f.get("status") == "pair"]
    naked = [f for f in att if str(f.get("status", "")).startswith("naked")]
    sp = [sets[f["slug"]] for f in pairs if f.get("slug") in sets]
    e = [_num(s.get("edge_per_share")) for s in sp if _num(s.get("edge_per_share")) is not None]
    best = [_num((w.get("best") or {}).get("sum_per_share")) for w in wins if tday(w)]; best = [b for b in best if b is not None]
    last = []
    for f in att[-5:][::-1]:
        s = sets.get(f.get("slug")) or {}; sh = _num(f.get("shares")) or 0
        last.append(dict(t=_ts(f.get("start")) and f.get("start"), ct=str(f.get("signal_ct") or "")[11:16], status=f.get("status"),
                         cpp=round(f["cost"] / sh, 4) if sh and _num(f.get("cost")) is not None else None, net=_num(s.get("net_pnl"))))
    return dict(hb_age=round(now - ht, 1) if ht else None, paused=hb.get("risk_paused"), gate=0.98,
                pnl=round(sum(_num(s.get("net_pnl")) or 0 for s in sets.values()), 2), settled=len(sets),
                spotted_today=sum(1 for o in opp if tday(o)), filled_today=sum(1 for f in pairs if tday(f)),
                pairs=len(pairs), days=len({s.get("ct_day") for s in sp if s.get("ct_day")}),
                edge_c=round(sum(e) / len(e) * 100, 2) if e else None,
                naked_pct=round(len(naked) / len(att) * 100, 1) if att else None,
                windows_today=len(best), best_today=min(best) if best else None, last=last)

def _iso(v):
    try: return calendar.timegm(time.strptime(str(v)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception: return None
def _start(slug):
    try: return int(str(slug).rsplit("-", 1)[1])
    except Exception: return None
def _positions(d, desk, W, now, cur, recs, sett, summ, open_c):
    snaps = {}
    for r in _tail(os.path.join(d, "window_snapshots.jsonl"), 400):
        if r.get("slug"): snaps[r["slug"]] = _num(r.get("price_to_beat_twap60"))
    pre = "btc-updown-%s-" % desk
    lags = []
    for r in recs:
        if r.get("record") == "settlement" and r.get("official"):
            t, st = _iso(r.get("ts")), _start(r.get("slug"))
            if t and st: lags.append(t - st - W)
    lags.sort(); lag = lags[len(lags)//2] if len(lags) >= 5 else (1800 if desk == "15m" else 330)
    if desk == "15m": slugs = [x.get("slug") for x in (summ.get("open_slugs") or [])]
    else: slugs = [x["slug"] for x in open_c]
    recent = [r for r in sett if r.get("win") is not None and (_iso(r.get("ts")) or 0) > now - 150]
    want = set(slugs) | {r.get("slug") for r in recent}
    legs = {}
    for r in recs:
        k = r.get("slug")
        if k not in want: continue
        rt, lg = r.get("record"), r.get("leg")
        if rt == "leg":
            sh = _num(r.get("shares")) or 0; pr = _num(r.get("price")) or 0; fee = _num(r.get("fee")) or 0
            legs.setdefault(k, []).append((r.get("action") or "buy", r.get("side"), sh, pr, fee, r.get("strategy")))
        elif desk == "5m" and ((rt == "decision" and r.get("decision") == "candidate") or rt == "pair_entry"):
            legs.setdefault(k, []).append(("buy", r.get("side"), _num(r.get("shares")) or 0, _num(r.get("entry_price")) or 0, _num(r.get("fee")) or 0, lg))
        elif desk == "5m" and rt == "exit":
            legs.setdefault(k, []).append(("sell", r.get("side"), _num(r.get("shares")) or 0, _num(r.get("exit_price")) or 0, _num(r.get("fee")) or 0, "exit"))
    dec = {r.get("slug"): r for r in recs if r.get("record") == "decision" and r.get("decision") == "candidate"}
    out = []
    for k in list(dict.fromkeys(slugs + [r.get("slug") for r in recent])):
        st = _start(k)
        if st is None: continue
        L = legs.get(k, []); cost = 0.0; held = {"Up": 0.0, "Down": 0.0}; proceeds = 0.0; main = None; pair = False; exited = False
        for act, side, sh, pr, fee, tag in L:
            if act == "buy":
                cost += sh * pr + fee; held[side] = held.get(side, 0) + sh
                if main is None: main = dict(side=side, price=pr, stake=round(sh * pr, 2))
                else: pair = True
            else:
                proceeds += sh * pr - fee; held[side] = max(0, held.get(side, 0) - sh); exited = True
        dr = dec.get(k) or {}
        if main is None: main = dict(side=dr.get("side"), price=_num(dr.get("entry_price")), stake=_num(dr.get("size_usd")) or 14.0)
        ptb = snaps.get(k) or _num(dr.get("price_to_beat_twap60"))
        live = k == cur.get("slug")
        if live and _num(cur.get("price_to_beat_twap60")): ptb = _num(cur.get("price_to_beat_twap60"))
        final = snaps.get(pre + str(st + W))
        res = next((r for r in recent if r.get("slug") == k), None)
        out.append(dict(slug=k, side=main["side"], entry=main["price"], stake=main["stake"], start_ts=st, end_ts=st + W,
            cost=round(cost, 2) if L else None, pays_up=round(held["Up"] + proceeds, 2) if L else None,
            pays_down=round(held["Down"] + proceeds, 2) if L else None, pair=pair, exited=exited,
            ptb=ptb, now_twap=_num(cur.get("running_twap60")) if live else None, now_px=_num(cur.get("chainlink_price")) if live else None,
            final_twap=final, settle_lag_s=lag, settle_lag_n=len(lags),
            result=None if not res else dict(win=bool(res.get("win")), pnl=_num(res.get("paper_pnl_after_fees")), outcome=res.get("outcome"), ts=_iso(res.get("ts")))))
    return out

def _is_pair(r):
    """True when a settlement line is a pair lock (15m: exit_type pair_lock / strategy pair_locked; 5m: leg 'pair')."""
    return r.get("exit_type") == "pair_lock" or r.get("strategy") == "pair_locked" or r.get("leg") == "pair" or "pair" in (r.get("legs") or [])
