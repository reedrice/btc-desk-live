#!/usr/bin/env python3
"""Push encrypted BTC desk neon JSON to Firebase RTDB /live (default) or a secret GitHub Gist (USE_GIST=1) every INTERVAL s.
Blob: {"v":1,"salt":b64,"iv":b64,"ct":b64,"ts":epoch}; plaintext = gzip(JSON {"5m":...,"15m":...}).
Key = PBKDF2-SHA256(passphrase, salt, 200000) -> AES-256-GCM. No AI usage."""
import os, sys, json, time, gzip, base64, subprocess, secrets
sys.path.insert(0, '/workspace/btc5m-dashboard')
import neon_api
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
D = os.path.dirname(os.path.abspath(__file__))
USE_GIST = os.environ.get('USE_GIST') == '1'
INTERVAL = float(os.environ.get('INTERVAL', 30 if USE_GIST else 2.5))  # gist hits secondary limits; firebase fine
DB = 'https://btc-desk-live-default-rtdb.firebaseio.com'
import urllib.request, hashlib
FBS = open(os.path.join(D, '.firebase_secret')).read().strip()
last = None
GID = open(os.path.join(D, '.gist_id')).read().strip()
pw = open(os.path.join(D, '.passphrase')).read().strip().encode()
salt = secrets.token_bytes(16)
key = AESGCM(PBKDF2HMAC(hashes.SHA256(), 32, salt, 200000).derive(pw))
b64 = lambda b: base64.b64encode(b).decode()
while True:
    t0 = time.time()
    try:
        data = {k: neon_api.build_neon(k) for k in ('5m', '15m')}
        iv = secrets.token_bytes(12)
        ct = key.encrypt(iv, gzip.compress(json.dumps(data, default=str).encode()), None)
        blob = json.dumps({"v": 1, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct), "ts": time.time()})
        h = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
        if h == last:
            time.sleep(max(1, INTERVAL - (time.time() - t0))); continue
        if not USE_GIST:
            req = urllib.request.Request(f'{DB}/live.json?auth={FBS}', data=blob.encode(), method='PUT')
            try:
                urllib.request.urlopen(req, timeout=15).read(); last = h
                print(time.strftime('%H:%M:%S'), 'ok', len(blob), flush=True)
            except Exception as e:
                print(time.strftime('%H:%M:%S'), 'ERR', str(e).replace(FBS, '***')[:200], flush=True); time.sleep(10)
            time.sleep(max(1, INTERVAL - (time.time() - t0))); continue
        body = json.dumps({"files": {"live.json": {"content": blob}}})
        r = subprocess.run(['gh', 'api', '-X', 'PATCH', f'gists/{GID}', '--input', '-', '--silent'],
                           input=body.encode(), capture_output=True, timeout=30)
        print(time.strftime('%H:%M:%S'), 'ok' if r.returncode == 0 else 'ERR ' + r.stderr.decode()[:200], len(blob), flush=True)
        if r.returncode: time.sleep(180)
    except Exception as e:
        print(time.strftime('%H:%M:%S'), 'EXC', e, flush=True); time.sleep(10)
    time.sleep(max(1, INTERVAL - (time.time() - t0)))
