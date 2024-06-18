import copy
import os
import queue
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')
sys.path.append(os.getcwd())

import grpc
import store_pb2, store_pb2_grpc
from concurrent import futures
import time
import threading

class Node():
    def __init__(self, id, ip, port, weight, stub):
        self.id = id
        self.ip = ip
        self.port = port
        self.weight = weight
        self.stub = stub


def threading_wait(nodes, quorum, initial_value, type):
    response_queue = queue.Queue()
    def ask_quorum(node):
        if type == 'PUT':
            resp = node.stub.votePut(store_pb2.Empty())
        else:
            resp = node.stub.voteGet(store_pb2.Empty())
        
        if resp.success:
            response_queue.put(node.weight)

    pool = futures.ThreadPoolExecutor(max_workers = len(nodes))
    future_results = [pool.submit(ask_quorum, node) for key, node in nodes]

    current = initial_value
    objective = quorum

    while True:
        val = response_queue.get()
        current += val
        if current >= objective:
            break


class KeyValueStoreServicer(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, id, ip, port, weight, quorum, nodes):
        self.me = Node(id, ip, port, weight, None)
        self.nodes = nodes
        self.store = {}
        self.quorum = quorum
        self.store_lock = threading.Lock()
        self.vote_lock = threading.Lock()

    def put(self, request, context):
        key = request.key
        value = request.value

        while self.me.id is None:
            time.sleep(0.1)
        
        #votes = self.me.weight
        with self.vote_lock:
            nodes = self.nodes.items()
            threading_wait(nodes, self.quorum['write'], self.me.weight, 'PUT')
            
            self.store[key] = value
            for n_key, node in self.nodes.items():
                node.stub.commitPut(store_pb2.PutRequest(key=key, value=value))

        return store_pb2.PutResponse(success=True)
        
    def get(self, request, context):
        key = request.key
        
        with self.vote_lock:
            nodes = self.nodes.items()
            threading_wait(nodes, self.quorum['read'], self.me.weight, 'GET')
        
        with self.store_lock:
            if key in self.store:
                value = self.store[key]
                found = True
            else:
                value = ""
                found = False


        return store_pb2.GetResponse(value=value, found=found)

    def slowDown(self, request, context):
        time.sleep(request.seconds)
        return store_pb2.SlowDownResponse(success=True)

    def restore(self, request, context):
        return store_pb2.RestoreResponse(success=True)

    def votePut(self, request, context):
        return store_pb2.Vote(success=True)

            
    def commitPut(self, request, context):
        key = request.key
        value = request.value
        with self.store_lock:
            self.store[key] = value
        return store_pb2.PutResponse(success=True)

    def voteGet(self, request, context):
        return store_pb2.Vote(success=True)

    def restoreData(self, request, context):
        with self.store_lock:
            data = self.store.copy()
        return store_pb2.RestoreDataResponse(data=data)

    def registerNode(self, request, context):
        id = request.id
        ip = request.ip
        port = request.port
        weight = request.weight

        channel = grpc.insecure_channel(f'{ip}:{str(port)}')
        stub = store_pb2_grpc.KeyValueStoreStub(channel)
        
        with self.vote_lock:
            self.nodes[id] = Node(id, ip, port, weight, stub)
        
        return store_pb2.RegisterNodeResponse(success=True)
        
    def ping(self, request, context):
        pong = store_pb2.Pong(success=True)
        return pong

class BootstrapServicer(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, weights, quorum):
        self.stubs = {}
        self.nodes = {}
        self.weights = eval(weights)
        self.quorum = eval(quorum)
        self.vote_lock = threading.Lock()

    def discoverMe(self, request, context):
        with self.vote_lock: 
            try:
                ip = request.ip
                port = request.port
                node_id = port % 10

                connection = f'{ip}:{port}'

                # Respuesta para el nuevo nodo
                response = store_pb2.DiscoverMeResponse(success=True, id=node_id, weight=self.weights[port])

                # Request para registrar el nodo en los antiguos
                register_req = store_pb2.NodeParams(id=node_id, ip=ip, port=port, weight=self.weights[port])

                # Añade la información de quorum
                response.quorum.update(self.quorum)

                # Registra el nodo en los nodos existentes
                for nid, n_connection in self.nodes.items():
                    n_ip = n_connection.split(':')[0]
                    n_port = int(n_connection.split(':')[1])
                    reg_node = store_pb2.NodeParams(id=nid, ip=n_ip, port=n_port, weight=self.weights[n_port])
                    response.node_dict[nid].CopyFrom(reg_node) # Odio los putos protobuffers
                    self.stubs[nid].registerNode(register_req)

                # Añade el nuevo nodo a la lista de nodos
                if node_id not in self.nodes:
                    self.stubs[node_id] = store_pb2_grpc.KeyValueStoreStub(grpc.insecure_channel(connection))
                    self.nodes[node_id] = connection

                return response

            except Exception as e:
                context.set_code(grpc.StatusCode.UNKNOWN)
                context.set_details(f'Exception calling application: {str(e)}')
                return store_pb2.DiscoverMeResponse(success=False)
