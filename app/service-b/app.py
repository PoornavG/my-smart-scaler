from flask import Flask
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- A global variable to act as our "switch" ---
DELAY_ENABLED = False

@app.route("/api")
def service_b_api():
    global DELAY_ENABLED
    logger.info("Service B (v4 Togglable): Received request.")
    
    # --- Check if the delay switch is on ---
    if DELAY_ENABLED:
        logger.warning("Service B: Simulating 1-second delay...")
        time.sleep(1)
    # ------------------------------------------

    logger.info("Service B (v4 Togglable): Work complete, returning.")
    return "Hello from Service B (Togglable v4)"

# --- The admin endpoint to flip the switch ---
@app.route("/toggle-delay")
def toggle_delay():
    global DELAY_ENABLED
    # Flip the boolean value
    DELAY_ENABLED = not DELAY_ENABLED
    
    if DELAY_ENABLED:
        status = "ON"
    else:
        status = "OFF"
        
    logger.info(f"--- Service B Delay switch has been turned {status} ---")
    return f"Service B Delay is now: {status}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)