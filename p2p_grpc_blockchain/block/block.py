#coding:utf-8
from p2p_grpc_blockchain.proto import grpc_pb2
from p2p_grpc_blockchain.proto import grpc_pb2_grpc
from p2p_grpc_blockchain.synchronization import synchronization
from p2p_grpc_blockchain.enum.enum import *
# from p2p_grpc_blockchain.p2p import p2p
import time 
import hashlib
import re

_compiNum = re.compile("^\d+$")  # 判斷全數字用
_compiW = re.compile("^\w{64}")

def defferentTreeSyn(node):
    # 分支同步
    block = Chain.getBlockFromHeight(Chain.getHeight()-1)
    while not block.To(node):
        block = Chain.getBlockFromHash(block.pb2.previoushash)
    print("== Finish Synchronization of DIFFERENT_TREE ==")


def Task(node,stub,task,message):
    if task == BLOCKBROADCAST:
        response = stub.BlockBroadcast(message)
        print ("=> [Transaction]Status:%s" % response.value)

        # 被回報區塊不同分支,將對方同步自己
        defferentTreeSyn(node) if response.value == "DIFFERENT_TREE" else True
        # 原始碼
        # if response.value == "DIFFERENT_TREE":
        #     defferentTreeSyn(node)

        if response.value.find("TOO_NEW_BLOCK") > 0:
            # 被回報區塊太新，開始送區塊至節點
            height = int(response.value[0:response.value.index("TOO_NEW_BLOCK")])+1
            block = Chain.getBlockFromHeight(height)
            try:
                while block.pb2.height < message.height:
                    if not block.To(node):
                        raise Exception("defferentTreeSyn(node)")
                    block = Chain.getBlockFromHash(block.pb2.nexthash)
            except Exception as e:
                defferentTreeSyn(node)
            print("== Finish Synchronization of TOO_NEW_BLOCK ==")

        elif response.value.find("TOO_OLD_BLOCK") > 0:
            # 被回報區塊太老，開始同步至最新
            info = Chain.getHeight()+1
            currentlyHeight = int( response.value[0:response.value.find("TOO_OLD_BLOCK")] )
            info += -1 if Block.From(node,info) < 0 else 1
            while info < currentlyHeight :
                info += -1 if Block.From(node,info) < 0 else 1

            print("== Finish Synchronization of TOO_OLD_BLOCK ==")


class Transaction(grpc_pb2_grpc.TransactionServicer):
    def BlockBroadcast(self, request, context):
        # => 區塊
        # <= Status
        block = Block()
        block.pb2 = request
        print("=> [Transaction]Block:%s" % block.pb2.blockhash)
        
        status = Chain.addBlock(block.pb2.blockhash,block)
        print("<= [Transaction]Status:%s" % status )
        return grpc_pb2.Message(value = status)
    

class Block:
    def __init__(self):
        pass

    def firstblock(self):
        # 世區塊
        pb2 = grpc_pb2.Block(height = 0,ctime = "The May 21 12:43:56 2017",value = "盧老師區塊鏈",
            previoushash = ":)",blockhash = "",nexthash = "")
        _temp = pb2.SerializeToString()
        _sha256 = hashlib.sha256(_temp).hexdigest()
        self.pb2 = pb2
        pb2.blockhash = _sha256
        Chain.addBlock(_sha256,self)
        return self
        
    def create(self,value):
        # 建立區塊
        currentlyHeight = Chain.getHeight()
        previousblock = Chain.getBlockFromHeight(currentlyHeight)
        pb2 = grpc_pb2.Block(height = currentlyHeight+1,ctime = time.ctime(),value = str(value),
            previoushash = previousblock.pb2.blockhash,blockhash = "",nexthash = "")
        _temp = pb2.SerializeToString()
        _sha256 = hashlib.sha256(_temp).hexdigest()
        self.pb2 = pb2
        pb2.blockhash = _sha256
        
        Chain.addBlock(_sha256,self)
        return self
    
    def vertify(self):
        # 驗證區塊
        _temp = self.pb2
        pb2 = grpc_pb2.Block(height = _temp.height,ctime = _temp.ctime,value = _temp.value,
            previoushash = _temp.previoushash,blockhash = "",nexthash = "")
        _strpb2 = pb2.SerializeToString()
        _hash = hashlib.sha256(_strpb2).hexdigest()
        
        if _hash!=_temp.blockhash:
            # hash 計算失敗
            return ERROR_BLOCK_HASH_VERTIFY
        
        try:
            previousBlock = Chain.getBlockFromHeight(_temp.height-1)
        except Exception as e:
            print(e)
            print("????")
            # 超出高度 計算失敗
            return NOT_FOUND_BLOCK

        if previousBlock.pb2.blockhash!=_temp.previoushash:
            # 警告新區塊 與 前區塊 
            return WARNING_PREVIOUS_HASH_NOT_EQUAL
        
        return SUCCESS_VERTIFY

    @staticmethod
    def From(node,info):
        from p2p_grpc_blockchain.p2p import p2p
        # <= 給予區塊資訊
        # => 返回高度
        block = Block()
        info = grpc_pb2.Message(value = str(info))
        print("<= [From]info:%s" % str(info))
        response = p2p.Node.send(node,SERVICE * SYNCHRONIZATION + FROM,info)
        print("=> [From]Block:%s" % str(response.blockhash))
        block.pb2 = response
        v = block.vertify()
        if v == SUCCESS_VERTIFY:
            Chain.addBlock(block.pb2.blockhash,block)
            return int(block.pb2.height)
        elif v == WARNING_PREVIOUS_HASH_NOT_EQUAL:
            return -1
        raise Exception("Error Block.py From()")

    def To(self,node):
        from p2p_grpc_blockchain.p2p import p2p
        # <= Block
        # => SYNCHRONIZATION or NOT_SYNCHRONIZATION
        # 當與原鏈連結 及 self.pb2.previoushash == block.pb2.blockhash 
        # 返回 SYNCHRONIZATION 否則 NOT_SYNCHRONIZATION
        print("<= [To] Block:%s" % self.pb2.blockhash)
        response = p2p.Node.send(node,SERVICE * SYNCHRONIZATION + TO,self.pb2)
        print("=> [To] Response:%s" % response.value)
        return response.value == "SYNCHRONIZATION"

        # if response.value == "SYNCHRONIZATION":
        #     return True
        # return False
        
class Chain:
    _lastblock = ""
    _firstblock = ""
    _Chain = {}

    @staticmethod
    def getHeight():
        height = 0
        ptrBlock = _firstblock
        while ptrBlock.pb2.nexthash!="":
            try:
                ptrBlock = Chain._Chain[ptrBlock.pb2.nexthash]
            except Exception as e:
                # 高度差>2 或 不同鍊 時發生
                break;
            height += 1
        return height

    @staticmethod
    def getBlockFromHeight(height):
        ptrBlock = _firstblock
        for i in range(0,height):
            try:
                ptrBlock = Chain._Chain[ptrBlock.pb2.nexthash]
            except Exception as e :
                print(e)
                raise Exception("not found height: %d block" % height)
        return ptrBlock
        
    @staticmethod
    def getBlockFromHash(hashvalue):
        return Chain._Chain[hashvalue]
    
    @staticmethod
    def addBlock(key,block):
        if len(Chain._Chain) == 0:
            Chain._firstblock = block
            Chain._Chain[key] = block
            return

        result = block.vertify()
        if result == ERROR_BLOCK_HASH_VERTIFY:
            return "ERROR_BLOCK_HASH_VERTIFY"
        elif result == WARNING_PREVIOUS_HASH_NOT_EQUAL:
            print("WARNING_PREVIOUS_HASH_NOT_EQUAL")
            
        addBlockBeforeHeight = Chain.getHeight()
        Chain._Chain[key] = block

        if synchronization.flag :
            # 分支同步才會進入
            if Chain._Chain.has_key(block.pb2.previoushash):
                branchBlock = Chain.getBlockFromHash(block.pb2.previoushash)
                branchBlock.pb2.nexthash = block.pb2.blockhash
                currentlyHeight = Chain.getHeight()
                if currentlyHeight > addBlockBeforeHeight:
                    print("== Finish Synchronization of DIFFERENT_TREE ==")
                    return "HEIGHT_ADD"
            return "SYNC_STATUS"

        currentlyHeight = Chain.getHeight()
        
        if block.pb2.height - currentlyHeight == 1:
            lastBlock = Chain.getBlockFromHeight(currentlyHeight)
            if lastBlock.pb2.blockhash == block.pb2.previoushash:
                # 增加新區塊。
                lastBlock.pb2.nexthash = block.pb2.blockhash
                lastBlock = block
                print("=> get new block")
                return "HEIGHT_ADD"

            else:
                # 發現不同分支。
                print("=> different tree")
                synchronization.setBranchTarget(block.pb2.blockhash)
                return "DIFFERENT_TREE"
        

        if block.pb2.height > currentlyHeight:
            # 獲得太新區塊。
            print("=> get too new block")
            return "%dTOO_NEW_BLOCK" % currentlyHeight
        
        if currentlyHeight - addBlockBeforeHeight >= 1:
            return "HEIGHT_ADD"
        
        if block.pb2.height == currentlyHeight:
            lastBlock = Chain.getBlockFromHeight(currentlyHeight)
            if lastBlock.pb2.blockhash == block.pb2.blockhash:
                print("=> get repeat block")
                return "HAS_BLOCK"
            # 發現同高度不同分支。
            print("=> get equal height but different block")
            print("do nothing")
            return "DIFFERENT_TREE_AND_HEIGHT_EQUAL"

        if Chain._Chain.has_key(block.pb2.previoushash):
            # 同步時修改前一個區塊的 nexthash 以串起鏈
            previousBlock = Chain.getBlockFromHash( block.pb2.previoushash )
            if previousBlock.pb2.nexthash != block.pb2.blockhash:
                previousBlock.pb2.nexthash = block.pb2.blockhash
                print("=> change nexthash")
                return "CHANGE_NEXTHASH"
        
        if block.pb2.height < currentlyHeight:
            # 獲得太舊區塊
            print("=> get too old block")
            return "%dTOO_OLD_BLOCK" % currentlyHeight

        return "ERROR_HAVE_NOT_BLOCK_TYPE"

    @staticmethod
    def show():
        result = ""
        height = 0
        ptrBlock = _firstblock
        result += (u"height:%d\tctime:%s\tprevioushash:%s\tblockhash:%s\tnexthash:%s\tvalue:%s\r\n" % 
            (ptrBlock.pb2.height,ptrBlock.pb2.ctime,ptrBlock.pb2.previoushash,ptrBlock.pb2.blockhash,ptrBlock.pb2.nexthash,ptrBlock.pb2.value.decode('utf-8')));
        while ptrBlock.pb2.nexthash != "" :
            try:
                ptrBlock = Chain._Chain[ptrBlock.pb2.nexthash]
                result += (u"height:%d\tctime:%s\tprevioushash:%s\tblockhash:%s\tnexthash:%s\tvalue:%s\r\n" % 
                    (ptrBlock.pb2.height,ptrBlock.pb2.ctime,ptrBlock.pb2.previoushash,
                    ptrBlock.pb2.blockhash,ptrBlock.pb2.nexthash,ptrBlock.pb2.value.decode('utf-8')))
            except Exception as e:
                # 高度差>2 或 不同鍊 時發生
                break;
            height += 1
        return result
    @staticmethod
    def showtolist():
        result = []
        height = 0
        ptrBlock = _firstblock
        result.append(ptrBlock.pb2)
        while ptrBlock.pb2.nexthash != "" :
            try:
                ptrBlock = Chain._Chain[ptrBlock.pb2.nexthash]
                result.append(ptrBlock.pb2)
            except Exception as e:
                # 高度差>2 或 不同鍊 時發生
                break;
            height += 1
        return result
_firstblock = Block().firstblock()