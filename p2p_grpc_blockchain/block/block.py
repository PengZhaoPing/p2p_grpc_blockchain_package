#coding:utf-8
from p2p_grpc_blockchain.proto import grpc_pb2
from p2p_grpc_blockchain.proto import grpc_pb2_grpc
from p2p_grpc_blockchain.synchronization import synchronization
from p2p_grpc_blockchain.transaction import transaction
from p2p_grpc_blockchain.enum.enum import *
# from p2p_grpc_blockchain.p2p import p2p
import time 
import random
import hashlib
import re
import threading
from fractions import Fraction
_compiNum = re.compile("^\d+$")  # 判斷全數字用
_compiW = re.compile("^\w{64}")

def defferentTreeSyn(node):
    # 分支同步
    pass


def Task(node,stub,task,message):
    pass
    
mineBool=True
def __mining():
    global mineBool
    while True:
        while mineBool:
            try:
                
                block=Block()
                block.computeAnswer()
                Chain.addBlock(block.pb2.blockhash,block)
                block.ExchangeBlock()
            except Exception as e :
                print e
class Block:
    def __init__(self):
        self.txs=[]
        self.time=""
        pass
    def computeAnswer(self):

        while True:
            try :
                self.create()
                self.pb2.txshash.extend(transaction.Transaction.getPoolList())
                self.pb2.answer=str(random.random())
                strpb2=self.pb2.SerializeToString()
                blockhash=hashlib.sha256(strpb2).hexdigest()
                if int(blockhash,16)<int(self.pb2.difficulty,16):
                    self.pb2.blockhash=blockhash
                    break;
            except Exception as e:
                print (e)


        print ("mining Block: %d" % self.pb2.height)
        
        
        
    def firstblock(self):
        # 創世區塊
        blockhash="00002a3157a4c26c8f3f8f7785bc632602a4903125251f466c99e61afe92d976"
        pb2 = grpc_pb2.Block(height = 0 ,unixtime = str(1497414820) ,previoushash = "smile\(^_^)/",
            blockhash = blockhash ,difficulty = "417574686f723a4c757273756e2c20e79ba7e7919ee5b1b1e69599e68e88" , answer=str(0.164882779333) , txshash = [])
        self.pb2 = pb2
        Chain.addBlock(blockhash,self)
        return self
        
        
    def create(self):
        # 建立區塊
        try:
            currentlyHeight = Chain.getHeight()
            previousblock = Chain.getBlockFromHeight(currentlyHeight)
            pb2 = grpc_pb2.Block(height = currentlyHeight+1,unixtime = str(time.time()),
                previoushash = previousblock.pb2.blockhash,blockhash = "",difficulty = Chain.getDifficulty(),answer = "" ,txshash = [] )
            self.pb2 = pb2
            return self
        except Exception as e:
            print (e)
    
    def vertify(self):
        # 驗證區塊
        tempblock = self.pb2
        pb2 = grpc_pb2.Block(height = tempblock.height,unixtime = tempblock.unixtime,previoushash=tempblock.previoushash,
            blockhash = "", difficulty = tempblock.difficulty , answer = tempblock.answer , txshash = tempblock.txshash)
        strpb2 = pb2.SerializeToString()
        blockhash = hashlib.sha256(strpb2).hexdigest()
        

        if blockhash!=tempblock.blockhash:
            # hash 計算失敗
            return ERROR_BLOCK_HASH_VERTIFY
        try:
            previousBlock = Chain.getBlockFromHeight(tempblock.height-1)
        except Exception as e:
            return NOT_FOUND_BLOCK
        if previousBlock.pb2.blockhash!=tempblock.previoushash:
            # 警告新區塊 與 前區塊 
            return WARNING_PREVIOUS_HASH_NOT_EQUAL
        
        return SUCCESS_VERTIFY
    @staticmethod
    def ExchangeBlock():
        from p2p_grpc_blockchain.p2p import p2p
        box=Chain.getBlockFromHeight(Chain.getHeight()).pb2
        print("<= [ExchangeBlock]")
        print box
        p2p.Node.broadcast(SERVICE * SYNCHRONIZATION + EXCHANGEBLOCK,box)
    @staticmethod
    def ExchangeBlockRecv(response):
        print("=> [ExchangeBlock]")
        print response
        box=Block()
        box.pb2=response
        Chain.addBlock(box.pb2.blockhash,box)
    @staticmethod
    def From(info):
        from p2p_grpc_blockchain.p2p import p2p
        # <= 給予區塊資訊
        # => 返回高度
                
        info = grpc_pb2.Message(value = str(info))
        print("<= [From]info:%s" % str(info))
        p2p.Node.broadcast(SERVICE * SYNCHRONIZATION + BLOCKFROM,info)
        

    @staticmethod
    def FromRecv(response):
        print("=> [From]Block:%s" % str(response.blockhash))
        block = Block()
        block.pb2 = response
        Chain.addBlock(block.pb2.blockhash,block)

    def To(self):
        from p2p_grpc_blockchain.p2p import p2p
        # <= Block
        # => SYNCHRONIZATION or NOT_SYNCHRONIZATION
        # 當與原鏈連結 及 self.pb2.previoushash == block.pb2.blockhash 
        # 返回 SYNCHRONIZATION 否則 NOT_SYNCHRONIZATION
        print("<= [To] Block:%s" % self.pb2.blockhash)
        threading.Thread( target=p2p.Node.broadcast,args=(SERVICE * SYNCHRONIZATION + BLOCKTO,self.pb2) ).start()
        
        
    @staticmethod
    def ToRecv(response):
        from p2p_grpc_blockchain.p2p import p2p
        print("=> [To] Status:%s" % response.value)
        if response.value.find("TOO_HIGH")>=0:
            height=response.value[:response.value.find("TOO_HIGH")]
            for i in range(1,Chain.getHeight()-int(height)+1):
                print ("send %d" % int(height)+i )
                box = Chain.getBlockFromHeight( int(height)+i )
                threading.Thread( target=p2p.Node.broadcast,args=(SERVICE * SYNCHRONIZATION + BLOCKTO,box.pb2) ).start()

        elif response.value.find("TOO_LOW")>=0:
            height=response.value[:response.value.find("TOO_LOW")]
            print (height)
            

        elif response.value=="HAS_BLOCK":
            
            pass

        elif response.value.find("BRANCH_SYNC")>=0:
            height=response.value[:response.value.find("BRANCH_SYNC")]
            box = Chain.getBlockFromHeight( int(height)-1 )
            threading.Thread( target=p2p.Node.broadcast,args=(SERVICE * SYNCHRONIZATION + BLOCKTO,box.pb2) ).start()
            
            

        
class Chain:
    _blockFromHeight = {}
    _blockFromHash = {}
    _Height=0
    @staticmethod
    def getHeight():
        return Chain._Height


    @staticmethod
    def getBlockFromHeight(height):
        try:
            resultBlock = Chain._blockFromHeight[height]
            return resultBlock
        except Exception as e:
            time.sleep(1)
            Block.From(height)
            raise Exception("not found height: %d block" % height)


    @staticmethod
    def getBlockFromHash(hashvalue):
        try:
            resultBlock = Chain._blockFromHash[hashvalue]
            return resultBlock
        except Exception as e:
            time.sleep(1)
            Block.From(height)
            raise Exception("not found blockhash: %d block" % hashvalue)
    
    @staticmethod
    def getDifficulty():
        if Chain.getHeight() >= 100:
            start = ((Chain.getHeight())//100-1)*100
            timetotal=0
            if start >= 0:
                for i in xrange(start,start+100):
                    previousTime=Chain.getBlockFromHeight(i).pb2.unixtime
                    nextTime=Chain.getBlockFromHeight(i+1).pb2.unixtime
                    timetotal += float(nextTime) - float(previousTime)
                proportion=Fraction(timetotal)/6000
                proportion= Fraction(4) if proportion > Fraction(4) else Fraction(0.25) if proportion < Fraction(0.25) else proportion
                return ( "%x" % int(int(Chain.getBlockFromHeight(start+100).pb2.difficulty,16)*proportion) )
            
        return "417574686f723a4c757273756e2c20e79ba7e7919ee5b1b1e69599e68e88"


    @staticmethod
    def addBlock(key,block):
        global mineBool

        if len(Chain._blockFromHeight) == 0:
            Chain._blockFromHeight[block.pb2.height]=block
            Chain._blockFromHash[key] = block
            return "ADD_BLOCK"
        

        
        
        if Chain._blockFromHash.has_key(block.pb2.blockhash):
            if not Chain._blockFromHeight.has_key(block.pb2.blockhash):
                Chain._blockFromHeight[key] = block
            return "HAS_BLOCK"

        
        if block.pb2.height - Chain.getHeight() == 1:
            transaction.Transaction.loadtxs(block.pb2.txshash)
            Chain._Height=block.pb2.height
            Chain._blockFromHash[key] = block
            Chain._blockFromHeight[Chain.getHeight()] = block
            mineBool=False
            if block.pb2.previoushash == Chain.getBlockFromHeight(block.pb2.height-1).pb2.blockhash :
                return "ADD_BLOCK"
            return "BRANCH_SYNC1"

        elif not Chain._blockFromHash.has_key(block.pb2.blockhash):
            transaction.Transaction.loadtxs(block.pb2.txshash)
            if block.pb2.height > Chain.getHeight():
                Chain._Height=block.pb2.height
                Chain._blockFromHeight[block.pb2.height] = block
            Chain._blockFromHash[key] = block
            mineBool=False
            return "BRANCH_SYNC2"

        elif block.pb2.height > Chain.getHeight():
            transaction.Transaction.loadtxs(block.pb2.txshash)
            Chain._Height=block.pb2.height
            Chain._blockFromHash[key] = block
            Chain._blockFromHeight[block.pb2.height] = block
            mineBool=False
            return "TOO_HIGH"

        

        elif block.pb2.height == Chain.getHeight():
            return "SAME_HEIGHT"
        
        elif block.pb2.height < Chain.getHeight():
            return "TOO_LOW"
        
        return "ERROR"

    @staticmethod
    def showtolist():
        result = []
        block=Chain.getBlockFromHeight(Chain.getHeight())
        result.append(block)
        while Chain._blockFromHash.has_key(block.pb2.previoushash):
            block=Chain.getBlockFromHash(block.pb2.previoushash)
            result.append(block)
        return result
    
    @staticmethod
    def reindex():
        global mineBool
        while True:
            
            while not mineBool:
                temp={}
                block=Chain.getBlockFromHeight(Chain.getHeight())
                temp[block.pb2.height]=block
                try:
                    while True: 
                        if Chain._blockFromHash.has_key(block.pb2.previoushash):
                            block=Chain.getBlockFromHash(block.pb2.previoushash)
                            temp[block.pb2.height]=block
                            if block.pb2.height == 0:
                                mineBool=True
                                break
                        else:
                            Block.From(block.pb2.previoushash)
                            
                except Exception as e:
                    print (e)
                Chain._blockFromHeight=temp
                
            
_firstblock = Block().firstblock()



print _firstblock
threading.Thread(target=__mining).start()
threading.Thread(target=Chain.reindex).start()