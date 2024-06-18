import subprocess
import yaml
import os
import signal
import sys
import time

master_process = None
slave_processes = []

def start_master():
    global master_process
    try:
        master_process = subprocess.Popen([sys.executable, "centralized_utils/master.py"])
    except Exception as e:
        print(f"Error starting master process: {e}", file=sys.stderr)
        sys.exit(1)

def start_slave(slave_id):
    try:
        slave_process = subprocess.Popen([sys.executable, "centralized_utils/slave.py", str(slave_id)])
        slave_processes.append(slave_process)
    except Exception as e:
        print(f"Error starting slave process {slave_id}: {e}", file=sys.stderr)

def handle_sigterm(signum, frame):
    print("SIGTERM received. Shutting down...")

    # Terminate master process
    if master_process:
        try:
            master_process.terminate()
            master_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            master_process.kill()

    # Terminate slave processes
    for slave_process in slave_processes:
        try:
            slave_process.terminate()
            slave_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            slave_process.kill()

    sys.exit(0)

def start_grpc_server():
    """Start the gRPC server as a subprocess."""
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    server_script_path = os.path.join(project_dir, 'centralized.py')
    server_process = subprocess.Popen([sys.executable, server_script_path])
    time.sleep(2)
    return server_process

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, handle_sigterm)

    with open('centralized_config.yaml', 'r') as f:
        config = yaml.safe_load(f)


    master_config = config.get('master')
    slaves_config = config.get('slaves', [])

    # Start master
    start_master()
    time.sleep(3)

    # Start slaves
    for slave_config in slaves_config:
        start_slave(slave_config['id'])

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server interrupted by user. Exiting...")
        handle_sigterm(None, None)  # Call the SIGTERM handler manually to ensure cleanup
