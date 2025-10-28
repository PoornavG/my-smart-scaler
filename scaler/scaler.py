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
MAX_REPLICAS = 5 # Set a max replica count
MIN_REPLICAS = 1 # Set a min replica count
NAMESPACE = "default" # Kubernetes namespace

# --- NEW: Cooldown period, as you requested ---
COOLDOWN_SECONDS = 60 # Wait 60 seconds after any scaling action
# This variable will track the time of our last action
last_scale_time = 0

# Map metric service.name to Kubernetes deployment name
SERVICES_TO_MONITOR = {
    "frontend-service": "frontend-deployment",
    "service-a": "service-a-deployment",
    "service-b": "service-b-deployment",
}
# We will only scale down the 'worker' services
SERVICES_TO_SCALE_DOWN = {
    "service-a": "service-a-deployment",
    "service-b": "service-b-deployment",
}


def get_k8s_api():
    """Loads Kubernetes configuration (in-cluster or local)."""
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

def get_average_latency_ms(prom_client, service_name, span_kind, range_sec="1m"):
    """
    Queries Prometheus for the average latency of a specific service
    and span_kind over a given time range.
    
    Calculated as: sum(rate(sum)) / sum(rate(count))
    """
    try:
        # PromQL query for the SUM of latencies
        query_suffix = f'{{service_name="{service_name}", span_kind="{span_kind}"}}[{range_sec}]'
        latency_sum_query = f'sum(rate(latency_milliseconds_sum{query_suffix}))'
        latency_count_query = f'sum(rate(latency_milliseconds_count{query_suffix}))'

        result_sum = prom_client.custom_query(query=latency_sum_query)
        result_count = prom_client.custom_query(query=latency_count_query)

        if not result_sum or not result_count or not result_sum[0].get('value') or not result_count[0].get('value'):
            logging.warning(f"No latency data found for service: {service_name}, span_kind: {span_kind}")
            return 0.0  # Return 0 if no data

        total_latency_sum = float(result_sum[0]['value'][1])
        total_latency_count = float(result_count[0]['value'][1])

        if total_latency_count == 0:
            logging.info(f"No requests observed for service: {service_name}, span_kind: {span_kind}")
            return 0.0  # No requests, so latency is 0

        avg_latency_ms = total_latency_sum / total_latency_count
        return avg_latency_ms

    except Exception as e:
        logging.error(f"Error querying latency for {service_name} ({span_kind}): {e}")
        return None # Return None on error

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
        # --- NEW: Set the cooldown timer ---
        last_scale_time = time.time()
    except Exception as e:
        logging.error(f"Failed to scale {deployment_name}: {e}")

# --- Main Loop ---
def main_loop():
    logging.info("--- Custom Scaler Started (v3 - Scale Up/Down with Cooldown) ---")
    k8s_api = get_k8s_api()
    prom = get_prometheus_connection()

    global last_scale_time
    # Initialize to allow immediate first check
    last_scale_time = time.time() - COOLDOWN_SECONDS 

    if not prom:
        logging.error("Could not connect to Prometheus. Exiting.")
        return

    while True:
        try:
            # --- NEW: Cooldown Check ---
            current_time = time.time()
            if current_time < last_scale_time + COOLDOWN_SECONDS:
                wait_time = (last_scale_time + COOLDOWN_SECONDS) - current_time
                logging.info(f"In cooldown period. Waiting {int(wait_time)} more seconds...")
                time.sleep(15) # Sleep 15 to not spam logs
                continue # Skip to the next loop iteration

            # 1. Check overall transaction latency
            total_avg_latency = get_average_latency_ms(
                prom, "frontend-service", "SPAN_KIND_SERVER", QUERY_RANGE
            )

            if total_avg_latency is None:
                logging.info("Skipping loop, no data yet.")
                time.sleep(15)
                continue

            logging.info(f"Current frontend avg latency: {total_avg_latency:.2f} ms")

            # --- SCALE UP LOGIC ---
            if total_avg_latency > SLA_MS:
                logging.warning(
                    f"SLA VIOLATION! Latency ({total_avg_latency:.2f}ms) > SLA ({SLA_MS}ms)"
                )
                
                # 3. Find the bottleneck using "Self-Time"
                service_a_server_time = get_average_latency_ms(prom, "service-a", "SPAN_KIND_SERVER", QUERY_RANGE) or 0
                service_a_client_time = get_average_latency_ms(prom, "service-a", "SPAN_KIND_CLIENT", QUERY_RANGE) or 0
                service_b_server_time = get_average_latency_ms(prom, "service-b", "SPAN_KIND_SERVER", QUERY_RANGE) or 0

                service_a_self_time = service_a_server_time - service_a_client_time
                service_b_self_time = service_b_server_time

                logging.info(
                    f"Bottleneck check: "
                    f"Service A Self-Time = {service_a_self_time:.2f}ms, "
                    f"Service B Self-Time = {service_b_self_time:.2f}ms"
                )

                if service_a_self_time > service_b_self_time:
                    bottleneck_service_name = "service-a"
                else:
                    bottleneck_service_name = "service-b"
                
                k8s_deployment_name = SERVICES_TO_MONITOR[bottleneck_service_name]
                logging.warning(
                    f"Bottleneck identified: {bottleneck_service_name} "
                    f"({k8s_deployment_name})"
                )

                # 4. Decide to Scale
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
            
            # --- NEW: SCALE DOWN LOGIC ---
            else:
                logging.info("SLA OK. Checking for services to scale down...")
                scaled_down_one = False
                # Check all scalable services
                for service_name, k8s_deployment_name in SERVICES_TO_SCALE_DOWN.items():
                    if scaled_down_one:
                        break # Only scale down one service per loop
                        
                    current_replicas = get_current_replicas(k8s_api, k8s_deployment_name)
                    
                    if current_replicas is not None and current_replicas > MIN_REPLICAS:
                        new_count = current_replicas - 1
                        logging.info(
                            f"Scaling {k8s_deployment_name} DOWN from "
                            f"{current_replicas} to {new_count} replicas..."
                        )
                        scale_deployment(k8s_api, k8s_deployment_name, new_count)
                        scaled_down_one = True # Set flag to exit loop
                
                if not scaled_down_one:
                    logging.info("All services are at minimum replicas. No scale-down needed.")
            
            # Wait for 15 seconds before the next check
            time.sleep(15)

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main_loop()