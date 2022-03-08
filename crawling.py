
from kademlia.node import Node, NodeHeap
from kademlia.utils import gather_dict


class SpiderCrawl:
    """ 
    Find nodes or value based on key node
    """
    def __init__(self, protocol, keyNode, peers, ksize, alpha):
        """ 
        keyNode: find nodes or value based on this key
        peers: some nodes we know in the dht
        """
        self.protocol = protocol
        self.keyNode = keyNode
        self.ksize = ksize
        self.alpha = alpha
        
        # keep track of the closest k nodes to key node 
        self.nearest = NodeHeap(self.keyNode, self.ksize)
        self.nearest.push(peers)

        self.last_ids_crawled = []


    async def _find(self, rpcmethod):
        """ 
        Either call find_node or find_value
        1. query alpha nodes
        2. if result does change, query all nodes that haven't been queried
        3. repeat until all nodes in nearest are queried
        """

        count = self.alpha
        if self.nearest.get_ids() == self.last_ids_crawled:
            count = len(self.nearest)
        self.last_ids_crawled = self.nearest.get_ids()

        dicts = {}
        # query each un-queried node
        for peer in self.nearest.get_uncontacted()[:count]:
            dicts[peer.id] = rpcmethod(peer, self.keyNode)
            self.nearest.mark_contacted(peer)

        found = await gather_dict(dicts)
        return await self._nodes_found(found)

    async def _nodes_found(self, responses):
        raise NotImplementedError


class ValueSpiderCrawl(SpiderCrawl):
    """
    find the value for the key or return the closer nodes
    """
    def __init__(self, protocol, keyNode, peers, ksize, alpha):
        SpiderCrawl.__init__(self, protocol, keyNode, peers, ksize, alpha)

    async def find(self):
        return await self._find(self.protocol.call_find_value)

    async def _nodes_found(self, responses):
        
        nodes_without_response = []
        found_values = []

        for peerid, response in responses.items():
            response = ResponseWrapper(response)
            if not response.has_response():
                nodes_without_response.append(peerid)
            # if value for the key is found
            elif response.has_value():
                found_values.append(response.get_value())
            # if closer nodes are returned
            else:
                self.nearest.push(response.get_node_list())

        self.nearest.remove(nodes_without_response)

        # sanity check for the values found
        if found_values:
            return await self._handle_found_values(found_values)

        if self.nearest.have_contacted_all():
            return None
        return await self.find()
        
    async def _handle_found_values(self, values):
        """
        check if all values found are the same
        return the most frequent element
        """
        valueSet = set(values)
        if len(valueSet) > 1:
            print("Found different values for key")
        
        value = 0
        maxFreq = 0

        for v in valueSet:
            if values.count(v) > maxFreq:
                maxFreq = values.count(v)
                value = v
        
        return value
            


class NodeSpiderCrawl(SpiderCrawl):
    """
    find closest nodes to a given key node
    """
    async def find(self):
        return await self._find(self.protocol.call_find_node)

    async def _nodes_found(self, responses):
        
        nodes_without_response = []

        # add returned closer node to heap
        for peerid, response in responses.items():
            response = ResponseWrapper(response)
            if not response.has_response():
                nodes_without_response.append(peerid)
            else:
                self.nearest.push(response.get_node_list())

        # remove nodes that did not respond
        self.nearest.remove(nodes_without_response)

        # return the closest nodes we can find
        if (self.nearest.have_contacted_all()):
            return list(self.nearest)
        
        # keep looking for closer nodes
        return await self.find()
        

class ResponseWrapper:
    """
    prepare content of response
    perform sanity check on response
    """
    def __init__(self, response):
        self.response = response

    def has_response(self):
        return self.response[0]

    def has_value(self):
        return isinstance(self.response[1], dict)

    def get_value(self):
        return self.response[1]['value']

    def get_node_list(self):
        
        nodelist = []
        if self.response[1]:
            nodelist = self.response[1]

        result = []
        for nodeple in nodelist:
            result.append(Node(*nodeple))

        return result