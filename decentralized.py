import subprocess
import yaml
import signal
import sys
import time

node_processes = []

def start_boot_node(ip, port, weights, quorum):
    try:
        node_process = subprocess.Popen([sys.executable, "decentralized_utils/boot_node.py", str(ip), str(port), str(weights), str(quorum)])
        node_processes.append(node_process)
    except Exception as e:
        print(f"Error starting boot node process: {e}", file=sys.stderr)

def start_node(ip, port, boot_node_id, boot_node_port):
    try:
        node_process = subprocess.Popen([sys.executable, "decentralized_utils/node.py", str(ip), str(port), str(boot_node_id), str(boot_node_port)])
        node_processes.append(node_process)
    except Exception as e:
        print(f"Error starting node process {port}: {e}", file=sys.stderr)

def handle_sigterm(signum, frame):
    print("SIGTERM received. Shutting down...")

    # Terminate node processes
    for node_process in node_processes:
        try:
            node_process.terminate()
            node_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            node_process.kill()

    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, handle_sigterm)

    with open('decentralized_config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Start boot node
    boot_config = config.get('boot_node')
    start_boot_node(boot_config['ip'], boot_config['port'], config['weights'], config['quorum'])

    time.sleep(3) # Delay para que se inicialice el boot_node

    # Start regular nodes   
    nodes_config = config.get('nodes', [])
    for node_config in nodes_config[:3]:
        start_node(node_config['ip'], node_config['port'], boot_config['ip'], boot_config['port'])

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server interrupted by user. Exiting...")
        handle_sigterm(None, None) 
