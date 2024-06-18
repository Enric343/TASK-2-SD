import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')
sys.path.append(os.getcwd())

import grpc
from concurrent import futures
import time
import threading
import store_pb2, store_pb2_grpc


class KeyValueStoreServicer(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self):
        self.store = {}
        self.slaves = []
        self.slaves_lock = threading.Lock()

    def put(self, request, context):
        with self.slaves_lock:
            can_commit_responses = [slave.votePut(store_pb2.Empty()) for slave in self.slaves]
            if all(response.success for response in can_commit_responses):
                self.store[request.key] = request.value
                for slave in self.slaves:
                    slave.commitPut(store_pb2.PutRequest(key=request.key, value=request.value))
                return store_pb2.PutResponse(success=True)
            else:
                return store_pb2.PutResponse(success=False)

    def get(self, request, context):
        if request.key in self.store:
            return store_pb2.GetResponse(value=self.store[request.key], found=True)
        else:
            return store_pb2.GetResponse(value="", found=False)

    def slowDown(self, request, context):
        time.sleep(request.seconds)
        return store_pb2.SlowDownResponse(success=True)

    def restore(self, request, context):
        self.slowdown = 0
        return store_pb2.RestoreResponse(success=True)

    def registerNode(self, request, context):
        slave_channel = grpc.insecure_channel(f"{request.ip}:{request.port}")
        slave_stub = store_pb2_grpc.KeyValueStoreStub(slave_channel)
        with self.slaves_lock:
            self.slaves.append(slave_stub)
        return store_pb2.RegisterNodeResponse(success=True)
    
    def restoreData(self, request, context): 
        return store_pb2.RestoreDataResponse(data=self.store)


class Slave(KeyValueStoreServicer):
    def votePut(self, request, context):
        return store_pb2.PutResponse(success=True)

    def commitPut(self, request, context):
        with self.slaves_lock:
            self.store[request.key] = request.value
            return store_pb2.PutResponse(success=True)
