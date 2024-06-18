import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')
sys.path.append(os.getcwd())

import grpc
import yaml
from concurrent import futures
import store_pb2_grpc, store_pb2
from decentralized_servicer import BootstrapServicer

def register_with_bootstrap(bootstrap_ip, bootstrap_port, weights, quorum):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    boot_server = BootstrapServicer(weights, quorum)
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(boot_server, server)
    server.add_insecure_port(f'{bootstrap_ip}:{bootstrap_port}')
    server.start()
    print(f"Bootstrap node started at {bootstrap_ip}:{bootstrap_port}")
    server.wait_for_termination()
    

if __name__ == '__main__':
    bootstrap_ip = sys.argv[1]
    bootstrap_port = int(sys.argv[2])
    weights = sys.argv[3]
    quorum = sys.argv[4]

    register_with_bootstrap(bootstrap_ip, bootstrap_port, weights, quorum)

