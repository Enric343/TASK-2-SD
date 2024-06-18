import json
import os
import sys
from threading import Thread
import threading
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')
sys.path.append(os.getcwd())

import grpc
from concurrent import futures
import store_pb2, store_pb2_grpc
from decentralized_servicer import KeyValueStoreServicer, Node
import sys
import yaml
import concurrent.futures


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

def discover_me(ip, port, boot_node_ip, boot_node_port):
    channel = grpc.insecure_channel(f'{boot_node_ip}:{boot_node_port}')
    stub = store_pb2_grpc.KeyValueStoreStub(channel)
    request = store_pb2.NodeParams(ip=ip, port=int(port))
    response = stub.discoverMe(request)
    return response

def serve(ip, port, boot_node_ip, boot_node_port):

    pool = futures.ThreadPoolExecutor(max_workers=10)
    data_file=f'{port}_data.json'

    server = grpc.server(pool)
    kv_store = KeyValueStoreServicer(None, ip, port, None, None, None)
    kv_store.store = load_data(data_file) 
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(kv_store, server)
    server.add_insecure_port(f'{ip}:{str(port)}')

    response = discover_me(ip, port, boot_node_ip, boot_node_port)
    if not response.success:
        exit()

    nodes = {}
    for k, v in response.node_dict.items():
        channel = grpc.insecure_channel(f'{v.ip}:{str(v.port)}')
        stub = store_pb2_grpc.KeyValueStoreStub(channel)
        nodes[k] = Node(v.id, v.ip, v.port, v.weight, stub)

    kv_store.me = Node(response.id, ip, port, response.weight, None)
    kv_store.quorum = response.quorum
    kv_store.nodes = nodes

    def server_thread(id, ip, port, nodes):
        time.sleep(2)
        print(f"({id}) checking connection")
        for node in nodes.values():
            ping = store_pb2.Ping(success=True)
            ip = node.ip
            port = node.port
            print(f"({id}) Connecting node {ip}:{port}")
            channel = grpc.insecure_channel(f'{ip}:{port}')
            stub = store_pb2_grpc.KeyValueStoreStub(channel)
            pong = stub.ping(ping)
            print(f"({id}) Got pong")

    thread = Thread(target=server_thread, args=(response.id, ip, port, nodes, ))
    thread.start()

    server.start()
    print(f"Node {id} started at {ip}:{str(port)}")

    # Iniciar hilo para copia de seguridad periódica
    backup_thread = threading.Thread(target=periodic_backup, args=(kv_store, data_file))
    backup_thread.daemon = True
    backup_thread.start()
    
    server.wait_for_termination()


if __name__ == '__main__':
    ip = sys.argv[1]
    port = sys.argv[2]
    boot_node_ip = sys.argv[3]
    boot_node_port = sys.argv[4]


    serve(ip, port, boot_node_ip, boot_node_port)

