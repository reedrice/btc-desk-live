#!/bin/bash
# Restart pusher.py if it dies. Start: nohup ./watchdog.sh >/dev/null 2>&1 &
cd /workspace/btc-desk-live
exec 9>watchdog.lock; flock -n 9 || exit 0
echo $$ > watchdog.pid
while true; do
  if ! { [ -f pusher.pid ] && kill -0 $(cat pusher.pid) 2>/dev/null; }; then
    nohup python3 pusher.py >> pusher.log 2>&1 & echo $! > pusher.pid
    echo "$(date) started pusher $!" >> watchdog.log
  fi
  [ $(stat -c%s pusher.log 2>/dev/null || echo 0) -gt 2000000 ] && : > pusher.log
  sleep 20
done
