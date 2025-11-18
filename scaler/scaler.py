import time
import os
import logging
from kubernetes import config, client
from prometheus_api_client import PrometheusConnect

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
SLA_MS = 500  # 500ms
QUERY_RANGE = "1m"
MAX_REPLICAS = 5
MIN_REPLICAS = 1
NAMESPACE = "default"
COOLDOWN_SECONDS = 60
IDLE_RPS_THRESHOLD = 0.5 

last_scale_time = 0

# --- NEW: Service map with real-world names ---
SERVICES_TO_MONITOR = {
    "web-storefront": "web-storefront-deployment",
    "inventory-service": "inventory-service-deployment",
    "payment-service": "payment-service-deployment",
}
# We only scale down the backend services
SERVICES_TO_SCALE_DOWN = {
    "inventory-service": "inventory-service-deployment",
    "payment-service": "payment-service-deployment",
}

def get_k8s_api():
    """Loads Kubernetes configuration."""
    try:
        config.load_incluster_config()
        logging.info("Loaded in-cluster Kubernetes config.")
    except config.ConfigException:
        logging.info("Could not load in-cluster config, falling back to local kubeconfig.")
        config.load_kube_config()
    return client.AppsV1Api()

def get_prometheus_connection():
    """Connects to the Prometheus server."""
    try:
        prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
        logging.info(f"Connected to Prometheus at {PROMETHEUS_URL}")
        return prom
    except Exception as e:
        logging.error(f"Failed to connect to Prometheus: {e}")
        return None

def get_avg_metric(prom_client, query):
    """A generic helper to run a query and get the average value."""
    try:
        result = prom_client.custom_query(query=query)
        if not result or not result[0].get('value'):
            return 0.0 # No data, return 0
        return float(result[0]['value'][1])
    except Exception as e:
        logging.error(f"Failed to query Prometheus: {query} | Error: {e}")
        return None

def get_average_latency_ms(prom_client, service_name, span_kind, range_sec="1m"):
    """
    Queries Prometheus for the average latency of a specific service
    and span_kind over a given time range.
    """
    query_suffix = f'{{service_name="{service_name}", span_kind="{span_kind}"}}[{range_sec}]'
    latency_sum_query = f'sum(rate(latency_milliseconds_sum{query_suffix}))'
    latency_count_query = f'sum(rate(latency_milliseconds_count{query_suffix}))'

    total_latency_sum = get_avg_metric(prom_client, latency_sum_query)
    total_latency_count = get_avg_metric(prom_client, latency_count_query)

    if total_latency_sum is None or total_latency_count is None:
        return None # Error occurred
    
    if total_latency_count == 0:
        logging.info(f"No requests observed for service: {service_name}, span_kind: {span_kind}")
        return 0.0  # No requests, so latency is 0

    return total_latency_sum / total_latency_count

def get_current_replicas(k8s_api, deployment_name):
    """Gets the current number of replicas for a deployment."""
    try:
        deployment = k8s_api.read_namespaced_deployment(
            name=deployment_name, namespace=NAMESPACE
        )
        return deployment.spec.replicas
    except Exception as e:
        logging.error(f"Failed to get replica count for {deployment_name}: {e}")
        return None

def scale_deployment(k8s_api, deployment_name, new_replica_count):
    """Scales a deployment to a new replica count."""
    global last_scale_time
    try:
        body = {"spec": {"replicas": new_replica_count}}
        k8s_api.patch_namespaced_deployment_scale(
            name=deployment_name, namespace=NAMESPACE, body=body
        )
        logging.info(f"Successfully scaled {deployment_name} to {new_replica_count} replicas.")
        last_scale_time = time.time()
    except Exception as e:
        logging.error(f"Failed to scale {deployment_name}: {e}")

# --- Main Loop ---
def main_loop():
    logging.info("--- Custom E-Commerce Scaler Started (v6 - Load-Aware) ---")
    k8s_api = get_k8s_api()
    prom = get_prometheus_connection()
    
    global last_scale_time
    last_scale_time = time.time() - COOLDOWN_SECONDS 

    if not prom:
        logging.error("Could not connect to Prometheus. Exiting.")
        return

    while True:
        try:
            # --- Cooldown Check ---
            current_time = time.time()
            if current_time < last_scale_time + COOLDOWN_SECONDS:
                wait_time = (last_scale_time + COOLDOWN_SECONDS) - current_time
                logging.info(f"In cooldown period. Waiting {int(wait_time)} more seconds...")
                time.sleep(15) 
                continue 

            # 1. Check overall transaction latency
            total_avg_latency = get_average_latency_ms(
                prom, "web-storefront", "SPAN_KIND_SERVER", QUERY_RANGE
            )

            if total_avg_latency is None:
                logging.info("Skipping loop, error querying Prometheus.")
                time.sleep(15)
                continue

            logging.info(f"Current checkout avg latency: {total_avg_latency:.2f} ms")

            # --- SCALE UP LOGIC ---
            if total_avg_latency > SLA_MS:
                logging.warning(
                    f"SLA VIOLATION! Latency ({total_avg_latency:.2f}ms) > SLA ({SLA_MS}ms)"
                )
                
                # 3. Find the bottleneck using "Self-Time"
                inventory_server_time = get_average_latency_ms(prom, "inventory-service", "SPAN_KIND_SERVER", QUERY_RANGE) or 0
                payment_server_time = get_average_latency_ms(prom, "payment-service", "SPAN_KIND_SERVER", QUERY_RANGE) or 0

                # Inventory's self-time = (Its total time) - (time it waited for Payment)
                inventory_self_time = inventory_server_time - payment_server_time
                # Payment has no client calls, so its server time IS its self-time
                payment_self_time = payment_server_time

                if inventory_self_time < 0: inventory_self_time = 0 

                logging.info(
                    f"Bottleneck check: "
                    f"Inventory Service Self-Time = {inventory_self_time:.2f}ms, "
                    f"Payment Service Self-Time = {payment_self_time:.2f}ms"
                )

                if inventory_self_time > payment_self_time:
                    bottleneck_service_name = "inventory-service"
                else:
                    bottleneck_service_name = "payment-service"
                
                k8s_deployment_name = SERVICES_TO_MONITOR[bottleneck_service_name]
                logging.warning(
                    f"Bottleneck identified: {bottleneck_service_name} "
                    f"({k8s_deployment_name})"
                )

                # 4. Decide to Scale Up
                current_replicas = get_current_replicas(k8s_api, k8s_deployment_name)
                
                if current_replicas is not None and current_replicas < MAX_REPLICAS:
                    new_count = current_replicas + 1
                    logging.info(f"Scaling {k8s_deployment_name} from "
                                 f"{current_replicas} to {new_count} replicas...")
                    scale_deployment(k8s_api, k8s_deployment_name, new_count)
                else:
                    logging.info(f"Already at max replicas ({MAX_REPLICAS}) or "
                                 f"could not get replica count for "
                                 f"{k8s_deployment_name}.")
            
            # --- SCALE DOWN LOGIC ---
            else:
                logging.info("SLA OK. Checking traffic load for scale-down...")
                
                # Check current requests per second (RPS)
                rps_query = f'sum(rate(latency_milliseconds_count{{service_name="web-storefront", span_kind="SPAN_KIND_SERVER"}}[{QUERY_RANGE}]))'
                current_rps = get_avg_metric(prom, rps_query)

                if current_rps is None:
                    logging.warning("Could not determine RPS. Skipping scale-down check.")
                
                elif current_rps < IDLE_RPS_THRESHOLD:
                    logging.info(f"Traffic is low ({current_rps:.2f} RPS). Checking for services to scale down...")
                    scaled_down_one = False
                    
                    for service_name, k8s_deployment_name in SERVICES_TO_SCALE_DOWN.items():
                        if scaled_down_one:
                            break 
                            
                        current_replicas = get_current_replicas(k8s_api, k8s_deployment_name)
                        
                        if current_replicas is not None and current_replicas > MIN_REPLICAS:
                            new_count = current_replicas - 1
                            logging.info(
                                f"Scaling {k8s_deployment_name} DOWN from "
                                f"{current_replicas} to {new_count} replicas..."
                            )
                            scale_deployment(k8s_api, k8s_deployment_name, new_count)
                            scaled_down_one = True 
                    
                    if not scaled_down_one:
                        logging.info("All services are at minimum replicas. No scale-down needed.")
                
                else: 
                    logging.info(f"SLA OK, but traffic is high ({current_rps:.2f} RPS). Holding current replica count.")

            
            time.sleep(15)

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main_loop()