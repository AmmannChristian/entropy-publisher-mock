#!/usr/bin/env bash
set -euo pipefail

# Restart the Docker Compose stack, prepare the Python environment, and launch
# the mock publisher process in the background.

# Mosquitto service name as defined in docker-compose.yml.
SERVICE_NAME="mosquitto"

# Runtime paths for the publisher script, log output, dependencies, and venv.
SCRIPT_PATH="$HOME/entropy-publisher-mock.py"
LOG_FILE="$HOME/publisher.log"
REQUIREMENTS_FILE="$HOME/requirements.txt"
VENV_DIR="$HOME/venv"

echo "[INFO] Stopping Docker Compose stack..."
docker compose down

echo "[INFO] Starting Docker Compose stack..."
docker compose up -d

echo "[INFO] Waiting for service '$SERVICE_NAME' to become healthy..."
# Poll the container health status every two seconds.
until [ "$(docker inspect --format='{{.State.Health.Status}}' $(docker compose ps -q "$SERVICE_NAME") 2>/dev/null)" = "healthy" ]; do
    echo "   -> Service not yet healthy, waiting..."
    sleep 2
done

echo "[INFO] Service '$SERVICE_NAME' is healthy."

# Create a virtual environment when one does not already exist.
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating new Python virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "[INFO] Activating Python virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies only when requirements.txt is available.
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "[INFO] Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "[WARNING] No requirements.txt found at $REQUIREMENTS_FILE. Skipping dependency installation."
fi

# Start the publisher as a detached process and redirect output to the log.
echo "[INFO] Starting Python publisher script in background..."
nohup python3 "$SCRIPT_PATH" > "$LOG_FILE" 2>&1 &

echo "[INFO] Process launched successfully."
echo "[INFO] Log output available at: $LOG_FILE"
