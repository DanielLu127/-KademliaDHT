"""
Package for interacting on the network at a high level.
"""
import random
import pickle
import asyncio
import logging

from kademlia.protocol import KademliaProtocol
from kademlia.utils import digest
from kademlia.storage import ForgetfulStorage
from kademlia.node import Node
from kademlia.crawling import ValueSpiderCrawl
from kademlia.crawling import NodeSpiderCrawl

log = logging.getLogger(__name__)


class Server:
    protocol_class = KademliaProtocol

    def __init__(self, ksize=20, alpha=3, node_id=None, storage=None):
        self.ksize = ksize
        self.alpha = alpha
        self.storage = storage or ForgetfulStorage()
        self.node = Node(node_id or digest(random.getrandbits(255)))
        self.transport = None
        self.protocol = None

    def stop(self):
        if self.transport is not None:
            self.transport.close()

    def _create_protocol(self):
        return self.protocol_class(self.node, self.storage, self.ksize)

    async def listen(self, port, interface='0.0.0.0'):
        loop = asyncio.get_event_loop()
        listen = loop.create_datagram_endpoint(self._create_protocol, local_addr=(interface, port))
        log.info("Node %i listening on %s:%i", self.node.long_id, interface, port)
        self.transport, self.protocol = await listen

    async def bootstrap(self, addrs):
        log.debug("Attempting to bootstrap node with %i initial contacts", len(addrs))
        cos = list(map(self.bootstrap_node, addrs))
        gathered = await asyncio.gather(*cos)
        nodes = [node for node in gathered if node is not None]
        spider = NodeSpiderCrawl(self.protocol, self.node, nodes, self.ksize, self.alpha)
        return await spider.find()

    async def bootstrap_node(self, addr):
        result = await self.protocol.ping(addr, self.node.id)
        if result[0]:
            return Node(result[1], addr[0], addr[1])
        else:
            None

    async def get(self, key):
        log.info("Looking up key %s", key)
        dkey = digest(key)

        # if this node has it, return it
        if self.storage.get(dkey) is not None:
            return self.storage.get(dkey)

        node = Node(dkey)
        nearest = self.protocol.router.find_neighbors(node)
        if not nearest:
            return None

        spider = ValueSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return await spider.find()

    async def set(self, key, value):
        log.info("setting '%s' = '%s' on netwoofeo3efoork", key, value)
        dkey = digest(key)
        node = Node(dkey)
        nearest = self.protocol.router.find_neighbors(node)
        if not nearest:
            return False

        nodes = await NodeSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha).find()

        biggest = 0
        for n in nodes:
            if n.distance_to(node) > biggest:
                biggest = n.distance_to(node)

        if self.node.distance_to(node) < biggest:
            self.storage[dkey] = value

        results = [self.protocol.call_store(n, dkey, value) for n in nodes]
        return any(await asyncio.gather(*results))


