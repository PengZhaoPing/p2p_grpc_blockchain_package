#coding:utf-8
from p2p_grpc_blockchain.proto import grpc_pb2
from p2p_grpc_blockchain.proto import grpc_pb2_grpc
# import p2p_grpc_blockchain.block as block
from p2p_grpc_blockchain.enum.enum import *
import threading
import time
import re


_compiNum = re.compile("^\d+$")  #判斷全數字用
_compiW = re.compile("^\w{64}")

class Synchronization(grpc_pb2.SynchronizationServicer):
    def From(self, request, context):
        from p2p_grpc_blockchain.block import block
        # => 請求(依據高度或Hash)
        # <= 區塊
        global _compiNum
        print("=> [From]Info:%s" % str(request.value))
        print("<= [From]Block:%s" % str(request.value))
        try :
            if _compiNum.search(request.value) != None:
                return block.Chain.getBlockFromHeight(int(request.value)).pb2
            elif _compiW.search(request.value)!= None:
                return block.Chain.getBlockFromHash(request.value).pb2
        except Exception as e:
            print(e)
        raise Exception("So Fast ,Wait... , Don't Close")
        
    def To(self, request, context):
        from p2p_grpc_blockchain.block import block
        # => Block
        # <= 如果高度增加 回傳 SYNCHRONIZATION ,否則 NOT_SYNCHRONIZATION
        global __BranchTarget,flag
        b = block.Block()
        b.pb2 = request
        print("=> [To] Block:%s" % b.pb2.blockhash)
        status = block.Chain.addBlock(b.pb2.blockhash,b)
        print("<= [To] Response:%sSYNCHRONIZATION" % ("" if "HEIGHT_ADD" == status else "NOT_") )
        if "HEIGHT_ADD" == status:
            flag = False
            __BranchTarget = ""
            return grpc_pb2.Message(value = "SYNCHRONIZATION")
        return grpc_pb2.Message(value = "NOT_SYNCHRONIZATION")
        # 簡化前
        # if "DIFFERENT_TREE" == status:
        #     return grpc_pb2.Message(value = "NOT_SYNCHRONIZATION")
        # if "SYNC_STATUS" == status:
        #     return grpc_pb2.Message(value = "NOT_SYNCHRONIZATION")
        # return grpc_pb2.Message(value = "NOT_SYNCHRONIZATION")
        

__BranchTarget = ""
flag = False
def setBranchTarget(hashvalue):
    global flag,__BranchTarget
    __BranchTarget,flag = hashvalue,True
    print("Status => Sync")
    threading.Thread(target = unlock).start()

def unlock():
    global flag,__BranchTarget
    time.sleep(600);
    __BranchTarget,flag = "",False

def Task(stub,task,message):
    return stub.From(message) if task == FROM else stub.To(message)
    # 等同
    # if task == FROM :
    #     return stub.From(message)
    # elif task == TO :
    #     return stub.To(message)