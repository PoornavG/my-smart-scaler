from flask import Flask, request
import os
import requests
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- NEW: A global variable to act as our "switch" ---
DELAY_ENABLED = False

# Get the downstream service URL for Service B
SERVICE_B_URL = os.environ.get("SERVICE_B_URL", "http://service-b.default/api")

@app.route("/api")
def service_a_api():
    global DELAY_ENABLED
    logger.info("Service A (v4 Togglable): Received request.")
    
    # --- NEW: Check if the delay switch is on ---
    if DELAY_ENABLED:
        logger.warning("Service A: Simulating 1-second delay...")
        time.sleep(1)
    # ------------------------------------------

    try:
        # Make a request to Service B
        logger.info(f"Service A: Calling Service B at {SERVICE_B_URL}")
        response = requests.get(SERVICE_B_URL)
        
        if response.status_code == 200:
            return f"Service A (v4) says: [{response.text}]"
        else:
            return f"Service A (v4): Error calling Service B. Status: {response.status_code}", 500

    except Exception as e:
        logger.error(f"Service A (v4): Exception calling Service B: {e}")
        return f"Service A (v4): Failed to connect to Service B. Error: {e}", 500

# --- NEW: The admin endpoint to flip the switch ---
@app.route("/toggle-delay")
def toggle_delay():
    global DELAY_ENABLED
    # Flip the boolean value
    DELAY_ENABLED = not DELAY_ENABLED
    
    if DELAY_ENABLED:
        status = "ON"
    else:
        status = "OFF"
        
    logger.info(f"--- Service A Delay switch has been turned {status} ---")
    return f"Service A Delay is now: {status}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)