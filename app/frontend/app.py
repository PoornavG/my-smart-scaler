from flask import Flask, request, render_template_string
import os
import requests
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get the downstream service URLs from environment variables
SERVICE_A_URL = os.environ.get("SERVICE_A_URL", "http://service-a.default/api")
SERVICE_B_URL = os.environ.get("SERVICE_B_URL", "http://service-b.default/api")

# --- NEW: Define the internal toggle URLs ---
SERVICE_A_TOGGLE_URL = "http://service-a/toggle-delay"
SERVICE_B_TOGGLE_URL = "http://service-b/toggle-delay"

# --- NEW: HTML Template for our Admin Panel ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scaler Demo Panel</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: grid; place-items: center; min-height: 90vh; background-color: #f4f7f6; }
        .container { background: #fff; padding: 2rem 3rem; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.07); text-align: center; }
        h1 { margin-top: 0; }
        .buttons { display: grid; grid-template-columns: 1fr; gap: 1rem; margin-top: 2rem; }
        button { font-size: 1rem; padding: 1rem 1.5rem; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; }
        .btn-checkout { background-color: #007aff; color: white; }
        .btn-checkout:hover { background-color: #0056b3; }
        .btn-toggle-a { background-color: #ff9500; color: white; }
        .btn-toggle-a:hover { background-color: #c67600; }
        .btn-toggle-b { background-color: #34c759; color: white; }
        .btn-toggle-b:hover { background-color: #289a44; }
        #message { margin-top: 1.5rem; font-size: 1.1rem; font-weight: 600; min-height: 30px; }
        #message.success { color: green; }
        #message.error { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Scaler Demo Panel</h1>
        <p>Continuously click "Run Checkout Test" to generate load.</p>
        <p id="message"></p>
        
        <div class="buttons">
            <button class="btn-checkout" onclick="runCheckout()">1. Run Checkout Test</button>
            <button class="btn-toggle-a" onclick="toggle('service-a')">2. Toggle Service-A Delay</button>
            <button class="btn-toggle-b" onclick="toggle('service-b')">3. Toggle Service-B Delay</button>
        </div>
    </div>

    <script>
        async function runCheckout() {
            const msgEl = document.getElementById('message');
            try {
                const response = await fetch('/checkout');
                if (!response.ok) throw new Error('Checkout failed');
                const text = await response.text();
                msgEl.textContent = 'Checkout OK: ' + text;
                msgEl.className = 'success';
            } catch (err) {
                msgEl.textContent = err.message;
                msgEl.className = 'error';
            }
            // Clear message after 3 seconds
            setTimeout(() => { msgEl.textContent = ''; }, 3000);
        }

        async function toggle(service) {
            const msgEl = document.getElementById('message');
            try {
                const response = await fetch(`/toggle/${service}`);
                if (!response.ok) throw new Error(`Toggle for ${service} failed`);
                const text = await response.text();
                msgEl.textContent = text;
                msgEl.className = 'success';
            } catch (err) {
                msgEl.textContent = err.message;
                msgEl.className = 'error';
            }
        }
    </script>
</body>
</html>
"""

# --- NEW: Main Admin Panel Route ---
@app.route("/")
def admin_panel():
    return render_template_string(HTML_TEMPLATE)

# --- This route is our main transaction ---
@app.route("/checkout")
def checkout():
    logger.info("Frontend: Received request at /checkout")
    try:
        logger.info(f"Frontend: Calling Service A at {SERVICE_A_URL}")
        response = requests.get(SERVICE_A_URL)
        
        if response.status_code == 200:
            return f"Frontend checkout successful! -> {response.text}"
        else:
            return f"Frontend: Error calling Service A. Status: {response.status_code}", 500
            
    except Exception as e:
        logger.error(f"Frontend: Exception calling Service A: {e}")
        return f"Frontend: Failed to connect to Service A. Error: {e}", 500

# --- NEW: Toggle Routes ---
@app.route("/toggle/service-a")
def toggle_service_a():
    logger.info("Frontend: Relaying toggle command to Service A")
    try:
        response = requests.get(SERVICE_A_TOGGLE_URL)
        return response.text, response.status_code
    except Exception as e:
        logger.error(f"Frontend: Failed to toggle Service A: {e}")
        return f"Failed to connect to Service A: {e}", 500

@app.route("/toggle/service-b")
def toggle_service_b():
    logger.info("Frontend: Relaying toggle command to Service B")
    try:
        response = requests.get(SERVICE_B_TOGGLE_URL)
        return response.text, response.status_code
    except Exception as e:
        logger.error(f"Frontend: Failed to toggle Service B: {e}")
        return f"Failed to connect to Service B: {e}", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
