#!/bin/bash
echo "Starting Sentient Redactor Service..."
echo "Starting Presidio service in background..."
cd /app
source /app/venv/bin/activate
python presidio_service.py &
PRESIDIO_PID=$!
echo "Presidio service started with PID: $PRESIDIO_PID"

echo "Waiting for Presidio service to be ready..."
sleep 5

echo "Starting Rust redactor service..."
./sentient-redactor-service &
RUST_PID=$!
echo "Rust service started with PID: $RUST_PID"

# Wait for both processes
wait $PRESIDIO_PID $RUST_PID
