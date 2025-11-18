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

# --- NEW: Updated service URL ---
PAYMENT_SERVICE_URL = os.environ.get("PAYMENT_SERVICE_URL", "http://payment-service/api")

@app.route("/api")
def inventory_api():
    global DELAY_ENABLED
    logger.info("Inventory Service: Received request.")
    
    # --- NEW: Check if the delay switch is on ---
    if DELAY_ENABLED:
        logger.warning("Inventory Service: Simulating SLOW database query (1s delay)...")
        time.sleep(1)
    # ------------------------------------------

    try:
        # Make a request to the Payment Service
        logger.info(f"Inventory Service: Calling Payment Service at {PAYMENT_SERVICE_URL}")
        response = requests.get(PAYMENT_SERVICE_URL)
        
        if response.status_code == 200:
            return f"Inventory OK -> {response.text}"
        else:
            return f"Inventory Service: Error calling Payment Service. Status: {response.status_code}", 500

    except Exception as e:
        logger.error(f"Inventory Service: Exception calling Payment Service: {e}")
        return f"Inventory Service: Failed to connect to Payment Service. Error: {e}", 500

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
        
    logger.info(f"--- Inventory Service Delay switch has been turned {status} ---")
    return f"Inventory Service Delay is now: {status}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)