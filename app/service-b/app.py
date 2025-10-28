from flask import Flask
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/api")
def service_b_api():
    logger.info("Service B: Received request at /api")
    
    # --- This is our "simulated" work ---
    # We add a small, random delay to simulate database work
    # and make our transaction latencies more realistic.
    logging.info("Service B: Simulating slow database query...")
    time.sleep(1)
    # ------------------------------------

    logger.info("Service B: Work complete, returning.")
    return "Hello from Service B (The final step!)"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)