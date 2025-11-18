from flask import Flask, request, render_template_string
import os
import requests
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- NEW: Updated service URL ---
SERVICE_INVENTORY_URL = os.environ.get("SERVICE_INVENTORY_URL", "http://inventory-service/api")

# --- NEW: Define the internal toggle URLs ---
SERVICE_INVENTORY_TOGGLE_URL = "http://inventory-service/toggle-delay"
SERVICE_PAYMENT_TOGGLE_URL = "http://payment-service/toggle-delay"

# --- NEW: E-Commerce Themed HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-Commerce Scaler Demo</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: grid; place-items: center; min-height: 90vh; background-color: #f4f7f6; color: #333; }
        .container { background: #fff; padding: 2rem 3rem; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); text-align: center; max-width: 600px; }
        h1 { margin-top: 0; color: #222; }
        p { color: #555; line-height: 1.5; }
        .buttons { display: grid; grid-template-columns: 1fr; gap: 1rem; margin-top: 2rem; }
        button { font-size: 1rem; padding: 1rem 1.5rem; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; }
        
        .btn-checkout { background-color: #007aff; color: white; border: 2px solid #007aff; }
        .btn-checkout:hover { background-color: #0056b3; }
        
        .btn-toggle-a { background-color: #ff9500; color: white; border: 2px solid #ff9500; }
        .btn-toggle-a:hover { background-color: #c67600; }
        
        .btn-toggle-b { background-color: #34c759; color: white; border: 2px solid #34c759; }
        .btn-toggle-b:hover { background-color: #289a44; }
        
        #message { margin-top: 1.5rem; font-size: 1.1rem; font-weight: 600; min-height: 30px; word-wrap: break-word; }
        #message.success { color: #289a44; }
        #message.error { color: #d93025; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Transaction-Aware Scaler Demo</h1>
        <p>This panel simulates an e-commerce checkout. Click "Buy Product" to run the transaction. Use the toggle buttons to create artificial latency in the backend microservices and watch the scaler (in your terminal) and Grafana (in your dashboard) react.</p>
        <p id="message"></p>
        
        <div class="buttons">
            <button class="btn-checkout" onclick="runCheckout()">1. Buy Product (Run Transaction)</button>
            <button class="btn-toggle-a" onclick="toggle('inventory-service')">2. Toggle SLOW Inventory DB (1s)</button>
            <button class="btn-toggle-b" onclick="toggle('payment-service')">3. Toggle SLOW Payment Gateway (1s)</button>
        </div>
    </div>

    <script>
        async function runCheckout() {
            const msgEl = document.getElementById('message');
            msgEl.textContent = 'Processing...';
            msgEl.className = '';
            try {
                const response = await fetch('/checkout');
                const text = await response.text();
                if (!response.ok) throw new Error(text);
                
                msgEl.textContent = text;
                msgEl.className = 'success';
            } catch (err) {
                msgEl.textContent = err.message;
                msgEl.className = 'error';
            }
            setTimeout(() => { if (!msgEl.className.includes('error')) msgEl.textContent = ''; }, 4000);
        }

        async function toggle(service) {
            const msgEl = document.getElementById('message');
            msgEl.textContent = `Toggling ${service}...`;
            msgEl.className = '';
            try {
                const response = await fetch(`/toggle/${service}`);
                const text = await response.text();
                if (!response.ok) throw new Error(text);
                
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
    logger.info("Storefront: Received request at /checkout")
    try:
        logger.info(f"Storefront: Calling Inventory Service at {SERVICE_INVENTORY_URL}")
        response = requests.get(SERVICE_INVENTORY_URL)
        
        if response.status_code == 200:
            return f"Checkout Successful! [{response.text}]"
        else:
            return f"Storefront: Error calling Inventory Service. Status: {response.status_code}", 500
            
    except Exception as e:
        logger.error(f"Storefront: Exception calling Inventory Service: {e}")
        return f"Storefront: Failed to connect to Inventory Service. Error: {e}", 500

# --- NEW: Toggle Routes ---
@app.route("/toggle/inventory-service")
def toggle_service_a():
    logger.info("Storefront: Relaying toggle command to Inventory Service")
    try:
        response = requests.get(SERVICE_INVENTORY_TOGGLE_URL)
        return response.text, response.status_code
    except Exception as e:
        logger.error(f"Storefront: Failed to toggle Inventory Service: {e}")
        return f"Failed to connect to Inventory Service: {e}", 500

@app.route("/toggle/payment-service")
def toggle_service_b():
    logger.info("Storefront: Relaying toggle command to Payment Service")
    try:
        response = requests.get(SERVICE_PAYMENT_TOGGLE_URL)
        return response.text, response.status_code
    except Exception as e:
        logger.error(f"Storefront: Failed to toggle Payment Service: {e}")
        return f"Failed to connect to Payment Service: {e}", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
