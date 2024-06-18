import json
import os
import sys
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')
sys.path.append(os.getcwd())

import grpc
from concurrent import futures
import store_pb2, store_pb2_grpc
from centralized_servicer import KeyValueStoreServicer, Slave
import yaml
import time
import sys

def discover_master(master_ip, master_port, slave_ip, slave_port):
    channel = grpc.insecure_channel(f'{master_ip}:{master_port}')
    stub = store_pb2_grpc.KeyValueStoreStub(channel)
    request = store_pb2.NodeParams(ip=slave_ip, port=slave_port)
    response = stub.registerNode(request)
    return response.success

def get_data_from_master(master_ip, master_port):
    channel = grpc.insecure_channel(f'{master_ip}:{master_port}')
    stub = store_pb2_grpc.KeyValueStoreStub(channel)
    response = stub.restoreData(store_pb2.Empty())  # Cambiado a restoreData
    return response.data

def serve_slave(slave_ip, slave_port, master_ip, master_port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    slave = Slave()
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(slave, server)
    server.add_insecure_port(f'{slave_ip}:{slave_port}')
    server.start()
    print(f"Servidor esclavo iniciado en {slave_ip}:{slave_port}")

    # Descubrir y registrarse con el maestro
    while True:
        try:
            if discover_master(master_ip, master_port, slave_ip, slave_port):
                print(f"Esclavo registrado con el maestro en {master_ip}:{master_port}")
                # Obtener datos del maestro
                data = get_data_from_master(master_ip, master_port)
                slave.store.update(data)
                print("Datos sincronizados con el maestro.")
                break
        except grpc.RpcError:
            print(f"Maestro no disponible en {master_ip}:{master_port}, reintentando en 5 segundos...")
            time.sleep(5)
    
    server.wait_for_termination()


if __name__ == '__main__':
    with open('centralized_config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    master_config = config['master']
    slaves_config = config['slaves']

    slave_id = int(sys.argv[1])
    slave_config = next(s for s in slaves_config if s['id'] == slave_id)

    serve_slave(slave_config['ip'], slave_config['port'], master_config['ip'], master_config['port'])
