from flask import Flask
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- NEW: A global variable to act as our "switch" ---
DELAY_ENABLED = False

@app.route("/api")
def payment_api():
    global DELAY_ENABLED
    logger.info("Payment Service: Received request.")
    
    # --- NEW: Check if the delay switch is on ---
    if DELAY_ENABLED:
        logger.warning("Payment Service: Simulating SLOW credit card gateway (1s delay)...")
        time.sleep(1)
    # ------------------------------------------

    logger.info("Payment Service: Work complete, returning.")
    return "Payment Approved"

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
        
    logger.info(f"--- Payment Service Delay switch has been turned {status} ---")
    return f"Payment Service Delay is now: {status}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)