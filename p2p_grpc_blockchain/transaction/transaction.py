from p2p_grpc_blockchain.proto import grpc_pb2
from p2p_grpc_blockchain.synchronization import synchronization
from p2p_grpc_blockchain.enum.enum import *
import time
import hashlib
import threading
class Transaction():
    Transactions={}
    TransactionsPool={}
    def create(self,body):
        pb2=grpc_pb2.Transaction(unixtime=str(time.time()),body=body,txhash="")
        strpb2=pb2.SerializeToString()
        txhash = hashlib.sha256(strpb2).hexdigest()
        pb2.txhash=txhash
        self.pb2=pb2
        Transaction.TransactionsPool[txhash]=self
        
        
        return self
    def txload(self,pb2tx):
        self.pb2=pb2tx
        Transaction.TransactionsPool[self.pb2.txhash]=self

    
    def Broadcast(self):
        from p2p_grpc_blockchain.p2p import p2p
        p2p.Node.broadcast(SERVICE*SYNCHRONIZATION+TRANSACTIONTO,self.pb2)
    
    @staticmethod
    def loadtxs(txshash):
        for txhash in txshash:
            if Transaction.TransactionsPool.has_key(txhash):
                Transaction.Transactions[txhash]=Transaction.TransactionsPool.pop(txhash)
            elif not Transaction.Transactions.has_key(txhash):
                Transaction.Transactions[txhash]=""
            else:
                print("It should not happen. transaction loadtx()")

    @staticmethod
    def getPoolList():
        result=[]
        iterator=Transaction.TransactionsPool.iterkeys()
        
        try:
            while True:
                txhash=iterator.next()
                result.append(txhash)
        except Exception as e:
            pass

        return result
    @staticmethod
    def getDictList():
        result=[]
        iterator=Transaction.Transactions.iterkeys()
        try:
            result.append(iterator.next())
        except Exception as e:
            pass
        return result
    @staticmethod
    def sync():
        from p2p_grpc_blockchain.p2p import p2p
        
        while True:
            item=Transaction.Transactions.iteritems()
            
            try:
                while True:
                    itemTuple=item.next()
                    if itemTuple[1]=="":
                        print ("<= txhash:%s" % itemTuple[0])
                        msg=grpc_pb2.Message(value=itemTuple[0])
                        p2p.Node.broadcast(SERVICE*SYNCHRONIZATION+TRANSACTIONFROM,msg)
            except Exception as e:
                pass

    @staticmethod
    def TransactionFromRecv(pb2tx):
        if pb2tx.body=="":
            return
        print ("=> unixtime:%s\tbody:%s" % (pb2tx.unixtime,pb2tx.body))
        tx=Transaction()
        tx.pb2=pb2tx
        Transaction.Transactions[tx.pb2.txhash]=tx
    
threading.Thread(target=Transaction.sync).start()