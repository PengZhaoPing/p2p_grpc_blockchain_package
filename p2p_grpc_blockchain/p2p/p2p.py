#coding:utf-8
import threading
import time
import os
import socket
import random
import re
from concurrent import futures
import grpc
from p2p_grpc_blockchain.block import block
from p2p_grpc_blockchain.synchronization import synchronization
from p2p_grpc_blockchain.proto import grpc_pb2
from p2p_grpc_blockchain.proto import grpc_pb2_grpc
from p2p_grpc_blockchain.enum.enum import *

PORT = ""
GET_SELFNODE_FALG = False
selfipport = ""
linkBroadcastFlag=False

class Node:
    __Nodes = set()

    #增加節點
    @staticmethod
    def add(target):
        if type(target) == str:
            if not (target in Node.__Nodes):
                print( "=> get new Node %s" % target )
                Node.__Nodes.add(target)

                def linkBroadcast():
                    global linkBroadcastFlag
                    if linkBroadcastFlag == False:
                        linkBroadcastFlag = True
                        while linkBroadcastFlag:
                            time.sleep(random.randint(1,60));
                            linkBroadcastBlock = block.Chain.getBlockFromHeight(block.Chain.getHeight())
                            print("<= [broadcast Block]:%s" % linkBroadcastBlock.pb2.blockhash)
                            Node.broadcast(SERVICE*TRANSACTION+BLOCKBROADCAST,linkBroadcastBlock.pb2)
                threading.Thread(target=linkBroadcast).start()

        elif type(target) == list:
            for i in target:
                Node.add(i)

        elif type(target) == tuple:
            Node.add("%s:%s" % target )

    #獲得節點清單
    @staticmethod
    def getNodesList():
        result = list()
        try:
            nodes = Node.__Nodes
            for i in nodes:
                result.append(i)
            return result
        except Exception as e :
            pass

    #廣播
    @staticmethod
    def broadcast(task,message = ""):
        global selfipport
        try:
            nodes = set()
            nodes.add(selfipport)
            nodes = Node.__Nodes-nodes
            for i in nodes:
                Node.send(i,task,message)
        except Exception as e :
            pass

    @staticmethod
    def passBroadcast(node,task,message):
        global selfipport
        try:
            nodes = set((node,selfipport))
            nodes = Node.__Nodes-nodes
            for i in temp:
                Node.send(i,task,message)
        except Exception as e :
            pass
        
    #送出
    @staticmethod
    def send(node,task,message = ""):
        try:
            channel = grpc.insecure_channel(node )
            taskType,task =task / SERVICE ,task % SERVICE
            if taskType == DESCOVERY:
                stub = grpc_pb2_grpc.DiscoveryStub(channel)
                if task ==EXCHANGENODE:
                    response = stub.ExchangeNode(grpc_pb2.Node(number = len(Node.__Nodes),ipport = Node.getNodesList() ))
                    for node in response.ipport :
                        Node.__Nodes.add(node)

            elif taskType == TRANSACTION:
                stub = grpc_pb2_grpc.TransactionStub(channel)
                block.Task(node,stub,task,message)
            
            elif taskType == SYNCHRONIZATION:
                stub = grpc_pb2_grpc.SynchronizationStub(channel)
                return synchronization.Task(stub,task,message)

        except Exception as e :
            Node.delNode(node)

        return


    @staticmethod
    def delNode(node):
        Node.__Nodes.remove(node)


    #得到 目前節點數
    @staticmethod
    def getLenght():
        return len(Node.__Nodes)

    



tempPort = 0
def __tempSocket(nodePort):
    # 當被動接收新節點 會開Socket 以知道對方IP
    global tempPort
    while tempPort == 0:
        port = PORT + 1
        sock = ""
        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(("0.0.0.0",port))
            sock.listen(1)
            tempPort = port
            (conn, client_addr) = sock.accept()
            tempPort = 0
            print("=> Node IP:%s" % client_addr[0])
            conn.send(client_addr[0])
            conn.close()
            sock.close()
            Node.add((client_addr[0],nodePort)) #獲得對方 "ip:port"
        except Exception as e:
            pass
            
#欲告訴對方你的 port 
def talkYouIP(nodePort):
    global tempPort
    if tempPort == 0:
        threading.Thread(target = __tempSocket, args = (nodePort,)).start()
    while tempPort == 0:
        time.sleep(1)
    return tempPort


class Discovery(grpc_pb2_grpc.DiscoveryServicer):
    # 交換節點清單
    def ExchangeNode(self, request, context):
        nodelist = Node.getNodesList()
        Node.add(list(request.ipport))
        return grpc_pb2.Node(number = Node.getLenght(),ipport = nodelist)


    # 告知對方他的ip,及自己的 grpc port,
    # 返回對方所開的port ->將再次連線取得自己ip
    def Hello(self , request , context):
        global PORT,selfipport
        selfIP = request.value[0:request.value.index('|')]
        Node.add((selfIP,PORT))
        selfipport= "%s:%s" % (selfIP,PORT)
        nodePort = request.value[request.value.index('|')+1:len(request.value)]
        print("=> Node Port:%s" % nodePort)
        port = talkYouIP(nodePort)
        return grpc_pb2.Message(value = str(port))



#交換節點清單迴圈
def exchangeLoop():
    while True :
        print("<= exchange list broadcast %s" %Node.getNodesList())
        Node.broadcast(SERVICE*DESCOVERY+EXCHANGENODE)
        time.sleep(30)


def __grpcNetworkStart():
    global PORT
    try:
        PORT = os.environ["GRPC_PORT"]
    except:
        PORT = "8001"
    print("grpc listen port:"+PORT)
    
    # grpc server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers = 10))
    grpc_pb2_grpc.add_DiscoveryServicer_to_server(Discovery(),server)
    grpc_pb2_grpc.add_TransactionServicer_to_server(block.Transaction(),server)
    # grpc_pb2_grpc.add_ConsensusServicer_to_server(Discovery(),server)
    grpc_pb2_grpc.add_SynchronizationServicer_to_server(synchronization.Synchronization(),server)

    server.add_insecure_port("[::]:%s" % PORT)
    server.start()

    threading.Thread(target = exchangeLoop).start()
    while True:
        time.sleep(1)


def grpcNetworkStart():
    # grpc 伺服器必須維持 故用Thread方式運作
    threading.Thread(target = __grpcNetworkStart).start()
    

def grpcJoinNode(target):
    global PORT ,GET_SELFNODE_FALG,selfipport
    target = str(target)
    compi = re.compile('^(\d{0,3}\.\d{0,3}\.\d{0,3}\.\d{0,3}):(\d{1,5})$')
    result = compi.match(target)

    # 判斷是否存在且曾加入過
    if result ==None or (target in Node.getNodesList() ):
        return False
    Node.add(target)

    # 判斷是否已取得自己IP
    if GET_SELFNODE_FALG:
        return True
    # Discovery.Hello()
    ip = result.group(1)
    print("<= grpc link to %s" % target)

    channel = grpc.insecure_channel( target )
    stub = grpc_pb2_grpc.DiscoveryStub(channel)
    HelloResponse = None
    try:
        HelloResponse = stub.Hello(grpc_pb2.Message(value = "%s|%s" % (ip,PORT) )) #target ip & self port
    except:
        return False
    helloPort = HelloResponse.value

    time.sleep(1)
    
    # 因不知道自己IP 故需要請對方告知自己
    # socket get my ip
    
    print("=> hello port:%s" % helloPort)
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    print("<= connect to socket will get myIP")
    sock.connect( (ip,int(helloPort)) )
    myIP = sock.recv(1024)
    print("=> get myIP:%s" % myIP)
    Node.add((myIP,PORT))
    selfipport= "%s:%s" % (myIP,PORT)
    GET_SELFNODE_FALG = True

    return True

