import asyncio
from rpcudp.protocol import RPCProtocol

from node import Node
from routing import RoutingTable
from utils import digest

class KademliaProtocol(RPCProtocol):
    def __init__(self, source, storage, k):
        RPCProtocol.__init__(self)
        self.router = RoutingTable(self, k, source)
        self.storage = storage
        self.source = source

    def get_refresh_ids(self):
        ids = []
        for bucket in self.router.lonely_buckets():
            rid = random.randint(*bucket.range).to_bytes(20, byteorder='big')
            ids.append(rid)
        return ids

    ## may change names
    def rpc_stun(self, sender):
        return sender
    def rpc_ping(self, sender, nodeid):
        source = Node(nodeid, sender[0], sender[1]) # node_id, ip, port
        self.welcome(source)
        return self.source.id
    def rpc_store(self, sender, nodeid, key, value):
        source = Node(nodeid, sender[0], sender[1])
        self.welcome(source)
        self.storage[key] = value
        return True
    def rpc_find_node(self, sender, nodeid, key):
        source = Node(nodeid, sender[0], sender[1])
        self.welcome(source)
        node = Node(key)
        neighbors = self.router.findNeighbors(node, exclude=source)
        return list(map(tuple, neighbors))
    def rpc_find_value(self, sender, nodeid, key):
        source = Node(nodeid, sender[0], sender[1])
        self.welcome(source)
        value = self.storage.get(key, None)
        if not value:
            return self.rpc_find_node(sender, nodeid, key)
        return {'value': value}


    async def call_find_node(self, node_to_ask, node_to_find):
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.find_node(address, self.source.id,
                                      node_to_find.id)
        return self.handle_call_response(result, node_to_ask)
    async def call_find_value(self, node_to_ask, node_to_find):
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.find_value(address, self.source.id,
                                       node_to_find.id)
        return self.handle_call_response(result, node_to_ask)
    async def call_ping(self, node_to_ask):
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.ping(address, self.source.id)
        return self.handle_call_response(result, node_to_ask)
    async def call_store(self, node_to_ask, key, value):
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.store(address, self.source.id, key, value)
        return self.handle_call_response(result, node_to_ask)

    def welcome(self, node):
        if self.router.is_new_node(node):
            for key, value in self.storage:
                keynode = Node(digest(key))
                neighbors = self.router.findNeighbors(keynode)
                if neighbors:
                    last = neighbors[-1].distance_to(keynode)
                    new_node_close = node.distance_to(keynode) < last
                    first = neighbors[0].distance_to(keynode)
                    this_closest = self.source.distance_to(keynode) < first
                if not neighbors or (new_node_close and this_closest):
                    asyncio.ensure_future(self.call_store(node, key, value))
            self.router.add_contact(node)

    def handle_call_response(self, result, node):
        if not result[0]:
            self.router.remove_contact(node)
            return result

        self.welcome(node)
        return result
