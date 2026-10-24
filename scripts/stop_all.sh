#!/usr/bin/env bash
PIDS=$(lsof -ti tcp:8001-8006)
if [ -n "$PIDS" ]; then
  kill $PIDS
  echo "Stopped processes on ports 8001-8006."
else
  echo "Nothing running on ports 8001-8006."
fi
