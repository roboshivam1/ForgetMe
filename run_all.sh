#!/usr/bin/env bash
cd "$(dirname "$0")"
mkdir -p logs
PIDS=()

start() {
  if [ -f "agents/$1/agent.py" ]; then
    .venv/bin/python -m "agents.$1.agent" > "logs/$1.log" 2>&1 &
    PIDS+=($!)
    echo "started $1 (log: logs/$1.log)"
  fi
}

cleanup() {
  echo
  echo "Stopping all agents..."
  kill "${PIDS[@]}" 2>/dev/null
  wait 2>/dev/null
  exit 0
}

trap cleanup INT TERM

start breach_scout
start risk_ranker
start eraser
start follow_up
sleep 2
start orchestrator

echo
echo "All agents running. Ctrl+C stops everything."
echo "Watch the orchestrator with: tail -f logs/orchestrator.log"
wait
