import os
import sys
import json
import grpc
import yaml
from concurrent import futures
from centralized_servicer import KeyValueStoreServicer
import store_pb2_grpc
import threading
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')
sys.path.append(os.getcwd())

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

def save_data(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def periodic_backup(kv_store, file_path, interval=1):
    while True:
        save_data(file_path, kv_store.store)
        time.sleep(interval)

def serve_master(master_ip, master_port, data_file):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    kv_store = KeyValueStoreServicer()

    # Cargar datos desde centralized_data.json
    kv_store.store = load_data(data_file)

    store_pb2_grpc.add_KeyValueStoreServicer_to_server(kv_store, server)
    server.add_insecure_port(f'{master_ip}:{master_port}')
    server.start()
    print(f"Servidor maestro iniciado en {master_ip}:{master_port}")

    # Iniciar hilo para copia de seguridad periódica
    backup_thread = threading.Thread(target=periodic_backup, args=(kv_store, data_file))
    backup_thread.daemon = True
    backup_thread.start()

    server.wait_for_termination()

if __name__ == '__main__':
    with open('centralized_config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    master_config = config['master']
    data_file = 'centralized_data.json'
    serve_master(master_config['ip'], master_config['port'], data_file)
