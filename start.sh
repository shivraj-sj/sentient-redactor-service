echo "Starting Sentient Redactor Service..."
echo "Starting Presidio service in background..."

/apps/venv/bin/python presidio_service.py & disown;
PRESIDIO_PID=$!
echo "Presidio service started with PID: $PRESIDIO_PID"


echo "Starting Rust redactor service..."
/apps/redactor-server & disown;
RUST_PID=$!
echo "Rust service started with PID: $RUST_PID"
