from distutils.core import setup

setup(
    name = 'p2p_grpc_blockchain',
    packages = ['p2p_grpc_blockchain','p2p_grpc_blockchain/block','p2p_grpc_blockchain/enum','p2p_grpc_blockchain/p2p','p2p_grpc_blockchain/proto','p2p_grpc_blockchain/synchronization','p2p_grpc_blockchain/transaction'],
    version = '0.42.08',
    description = 'p2p_grpc_blockchain',
    author = 'lursun & rslu',
    author_email = 'lursun914013@gmail.com , rslu2000@gmail.com',
    url = 'https://github.com/Lursun/p2p_grpc_blockchain_package/archive/v0.3.zip',
    keywords = ['blockchain','grpc','p2p'],
    classifiers = [],
)
