from flask import Flask, request
import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get the downstream service URL for Service B
SERVICE_B_URL = os.environ.get("SERVICE_B_URL", "http://service-b.default/api")

@app.route("/api")
def service_a_api():
    logger.info("Service A: Received request at /api")
    try:
        # Make a request to Service B
        logger.info(f"Service A: Calling Service B at {SERVICE_B_URL}")
        response = requests.get(SERVICE_B_URL)
        
        if response.status_code == 200:
            return f"Service A says: [{response.text}]"
        else:
            return f"Service A: Error calling Service B. Status: {response.status_code}", 500

    except Exception as e:
        logger.error(f"Service A: Exception calling Service B: {e}")
        return f"Service A: Failed to connect to Service B. Error: {e}", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)