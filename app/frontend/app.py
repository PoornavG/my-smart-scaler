from flask import Flask, request
import os
import requests
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get the downstream service URL from an environment variable
# 'service-a.default' is the default Kubernetes DNS name
# (service-name.namespace)
SERVICE_A_URL = os.environ.get("SERVICE_A_URL", "http://service-a.default/api")

@app.route("/")
def hello_world():
    logger.info("Frontend: Received request at /")
    return "Hello from Frontend! Visit /checkout to run a transaction."

@app.route("/checkout")
def checkout():
    logger.info("Frontend: Received request at /checkout")
    try:
        # Make a request to Service A
        logger.info(f"Frontend: Calling Service A at {SERVICE_A_URL}")
        response = requests.get(SERVICE_A_URL)
        
        # Check if the downstream call was successful
        if response.status_code == 200:
            return f"Frontend checkout successful! -> {response.text}"
        else:
            return f"Frontend: Error calling Service A. Status: {response.status_code}", 500
            
    except Exception as e:
        logger.error(f"Frontend: Exception calling Service A: {e}")
        return f"Frontend: Failed to connect to Service A. Error: {e}", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)