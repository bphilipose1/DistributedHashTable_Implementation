import sys
import threading
import hashlib
import socket
import pickle
import time

M = 3  # FIXME: 3 Test environment, normally = hashlib.sha1().digest_size * 8
NODES = 2**M
BUF_SZ = 4096  # socket recv arg
BACKLOG = 100  # socket listen arg
BASE_PORT = 43544  # for testing use port numbers on localhost at BASE_PORT+n

def hash_key(key):
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % NODES

class ModRange(object):
    """
    Range-like object that wraps around 0 at some divisor using modulo arithmetic.

    >>> mr = ModRange(1, 4, 100)
    >>> mr
    <mrange [1,4)%100>
    >>> 1 in mr and 2 in mr and 4 not in mr
    True
    >>> [i for i in mr]
    [1, 2, 3]
    >>> mr = ModRange(97, 2, 100)
    >>> 0 in mr and 99 in mr and 2 not in mr and 97 in mr
    True
    >>> [i for i in mr]
    [97, 98, 99, 0, 1]
    >>> [i for i in ModRange(0, 0, 5)]
    [0, 1, 2, 3, 4]
    """

    def __init__(self, start, stop, divisor):
        self.divisor = divisor
        self.start = start % self.divisor
        self.stop = stop % self.divisor
        # we want to use ranges to make things speedy, but if it wraps around the 0 node, we have to use two
        if self.start < self.stop:
            self.intervals = (range(self.start, self.stop),)
        elif self.stop == 0:
            self.intervals = (range(self.start, self.divisor),)
        else:
            self.intervals = (range(self.start, self.divisor), range(0, self.stop))

    def __repr__(self):
        """ Something like the interval|node charts in the paper """
        return ''.format(self.start, self.stop, self.divisor)

    def __contains__(self, id):
        """ Is the given id within this finger's interval? """
        for interval in self.intervals:
            if id in interval:
                return True
        return False

    def __len__(self):
        total = 0
        for interval in self.intervals:
            total += len(interval)
        return total

    def __iter__(self):
        return ModRangeIter(self, 0, -1)

class ModRangeIter(object):
    """ Iterator class for ModRange """
    def __init__(self, mr, i, j):
        self.mr, self.i, self.j = mr, i, j

    def __iter__(self):
        return ModRangeIter(self.mr, self.i, self.j)

    def __next__(self):
        if self.j == len(self.mr.intervals[self.i]) - 1:
            if self.i == len(self.mr.intervals) - 1:
                raise StopIteration()
            else:
                self.i += 1
                self.j = 0
        else:
            self.j += 1
        return self.mr.intervals[self.i][self.j]

class FingerEntry(object):
    """
    Row in a finger table.

    >>> fe = FingerEntry(0, 1)
    >>> fe
    
    >>> fe.node = 1
    >>> fe
    
    >>> 1 in fe, 2 in fe
    (True, False)
    >>> FingerEntry(0, 2, 3), FingerEntry(0, 3, 0)
    (, )
    >>> FingerEntry(3, 1, 0), FingerEntry(3, 2, 0), FingerEntry(3, 3, 0)
    (, , )
    >>> fe = FingerEntry(3, 3, 0)
    >>> 7 in fe and 0 in fe and 2 in fe and 3 not in fe
    True
    """
    def __init__(self, n, k, node=None):
        if not (0 <= n < NODES and 0 < k <= M):
            raise ValueError('invalid finger entry values')
        self.start = (n + 2**(k-1)) % NODES
        self.next_start = (n + 2**k) % NODES if k < M else n
        self.interval = ModRange(self.start, self.next_start, NODES)
        self.node = node

    def __repr__(self):
        """ Something like the interval|node charts in the paper """
        return ''.format(self.start, self.next_start, self.node)

    def __contains__(self, id):
        """ Is the given id within this finger's interval? """
        return id in self.interval

class ChordNode(object):
    def __init__(self, port, known_node = None):
        self.node = (port - BASE_PORT) % NODES
        self.finger = [None] + [FingerEntry(self.node, k) for k in range(1, M+1)]  # indexing starts at 1
        self.predecessor = None
        self.keys = {}
        self.joined = False
        if known_node is not None:
            self.buddy_port = self.lookup_node(known_node)
        
        #Then use TCP and pickle to listen for incomming connections
        listener_thread = threading.Thread(target=self.listener, args=(ChordNode.lookup_node(self.node),))
        listener_thread.daemon = True
        listener_thread.start()
        
        self.log(f'starting node {self.node} joining via buddy at port {known_node}')
        self.join_network(known_node)#join the network and use 'system assigned port number for itself'

        
        
    def listener(self, address):
        self.log(f'serve_forever({address})')
        listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener_socket.bind(address)
        listener_socket.listen()
        
        while True:
            conn, addr = listener_socket.accept()
            loaded_data = pickle.loads(conn.recv(BUF_SZ))
            procedure, argument1, argument2 = loaded_data
            
            #Spin up thread to handle request
            handle_thr = threading.Thread(target=self.handle_rpc, args=(conn, addr, procedure, argument1, argument2))
            handle_thr.start()
       
    def run(self):
        #Repeatedly run printing log_finger_table and sleep for 5 seconds
        while True:
            print('Heartbeat' + repr(self))
            time.sleep(5)

       
       
       
#FIGURE 6  - JOINING A NETWORK
    def join_network(self, np): #COMPLETELY FOLLOW PSEUDO CODE
        self.log(f"{self.node}.join({np})")
        #if the node recieved an existing network port number join it
        if np is not None:
            self.init_finger_table(np)
            self.update_others() # Move keys between (predacessor, N] from sucessor if any
            #self.log(f'Joined Existing Network with {known_node}')
        # if the port number is 0, node is by itself, start a new network
        else:
            #self.log('No Existing Network, Created a new Chord Network')
            for i in range(1, M+1):
                self.finger[i].node = self.node
                
            self.predecessor = self.node
        
        self.joined = True
        #start up run on a daemon thread
        run_thread = threading.Thread(target=self.run)
        run_thread.daemon = True
        run_thread.start()
            
            
        #self.log_finger_table()
            

    def init_finger_table(self, np): #COMPLETELY FOLLOWS PSEUDO CODE

        # Step 1: Initialize the first finger entry (successor)
        print('checkpoint1`')
        self.finger[1].node = self.call_rpc(np, 'find_successor', self.finger[1].start)
        print('checkpoint2')
        self.predecessor = self.call_rpc(self.successor, 's_predecessor')
        print(f'checkpoint3 - Attempting to update sucessor node {self.successor} predecessors value to: {self.node}')
        print(self.call_rpc(self.successor, 's_predecessor', self.node))
        print('checkpoint4')

        
        # Step 2:Populate the rest of the finger table
        for i in range(1, M):
            

            if self.finger[i + 1].start in ModRange(self.node, self.finger[i].node, NODES):
                self.finger[i + 1].node = self.finger[i].node
            else:
                self.finger[i + 1].node = self.call_rpc(np, 'find_successor', self.finger[i + 1].start)

        self.log(f'init_finger_table: {self.__repr__()}')
        
       
        

        
    def update_others(self):
        """ Update all other node that should have this node in their finger tables """
        print('update_others()')
        for i in range(1, M+1):  # find last node p whose i-th finger might be this node
            # FIXME: bug in paper, have to add the 1 +
            p = self.find_predecessor((1 + self.node - 2**(i-1) + NODES) % NODES)
            print(f'sending out to {p} update_others({self.node}, {i})')
            self.call_rpc(p, 'update_finger_table', self.node, i)

    def update_finger_table(self, s, i):
        self.log(f"{self.node}.update_finger_table({s},{i})")
        """ if s is i-th finger of n, update this node's finger table with s """
        # FIXME: don't want e.g. [1, 1) which is the whole circle --- FIXME: bug in paper, [.start
        if (self.finger[i].start != self.finger[i].node and s in ModRange(self.finger[i].start, self.finger[i].node, NODES)):
            print('update_finger_table({},{}): {}[{}] = {} since {} in [{},{})'.format(s, i, self.node, i, s, s, self.finger[i].start, self.finger[i].node))
            self.finger[i].node = s
            print('#', self.__repr__())
            p = self.predecessor  # get first node preceding myself
            self.call_rpc(p, 'update_finger_table', s, i)
            print(f'sending out to {p} update_others({s}, {i})')
            return str(self.__repr__())
        else:
            return 'did nothing {}'.format(self.__repr__())

        



    @property
    def successor(self):
        #self.log(f"{self.node}.successor()")
        #self.log(f"\t{self.node}.successor() --> {self.finger[1].node}")
        return self.finger[1].node

    @successor.setter
    def successor(self, id):
        self.finger[1].node = id
        self.log(f"{self.node}.successor()")
        self.log(f"\t{self.node}.successor() --> {self.finger[1].node}")
        

    def s_predecessor(self, id = None):
        self.log(self.__repr__())
        if id != None:
            self.predecessor = id
            self.log(f"{self.node}.predecessor({id})")
            self.log(f"\t{self.node}.p = {id}")
            self.log(f"\t{self.node}.predecessor({id}) --> <{self.node}: {self.__repr__()} {self.predecessor}>")
            return str(self.__repr__())
        else:
            self.log(f"{self.node}.predecessor()")
            self.log(f"\t{self.node}.predecessor() --> {self.predecessor}")
            return self.predecessor




#FIGURE 4 - FINDING NODES
    def find_successor(self, id): #COMPLETELY FOLLOWS PSEUDOCODE
        """ Ask this node to find id's successor = successor(predecessor(id))"""
        self.log(f"{self.node}.find_successor({id})")
        np = self.call_rpc(self.node, 'find_predecessor', id)
        result = self.call_rpc(np, 'successor')
        self.log(f"\t{self.node}.find_successor({id}) --> {result}")
        return result

    def find_predecessor(self, id):
        """ Ask this node to find id's predecessor """
        np = self.node
        while id not in ModRange(np + 1, self.call_rpc(np, 'successor') + 1, NODES):
            # Find the closest preceding finger for the given id
            np = self.call_rpc(np, 'closest_preceding_finger', id)
            
        #self.log(f"Entered find_predecessor...[{np}]")
        return np


    def closest_preceding_finger(self, id):
        '''Go through finger table and find closest bucket range that is BEFORE the target id'''
        self.log(f'{self.node}.closest_preceding_finger({id})')
        for i in range(M, 0, -1):  # Start at the end of the finger table
            if self.finger[i].node in ModRange(self.node + 1, id, NODES):  # If the finger is in the range of the target id
                self.log(f'\t{self.node}.closest_preceding_finger({id}) --> {self.finger[i].node}')
                return self.finger[i].node
        #self.log(f"No closest preceding finger found for {id}, returning self node: {self.node}")
        return self.node  # If no finger is found, return the current node






    #RPC SECTION
    @staticmethod
    def lookup_node(node_id):
        return 'localhost', BASE_PORT + node_id
    
    @staticmethod
    def lookup_addr(port, host = 'localhost'):
        return abs(BASE_PORT - int(port))

    def handle_rpc(self, client_conn, sender_addr, method, arg1, arg2):
        '''Unmarshal the RPC call process it and send the result back to the client'''
        #print(f'Handling {method} from {sender_addr[1]}')
        sender_node = self.lookup_addr(sender_addr[1])
        result = self.dispatch_rpc(sender_node, method, arg1, arg2)
        client_conn.sendall(pickle.dumps(result))   

        

    def dispatch_rpc(self, sender_node, method, arg1, arg2):
        ###self.log(f'Dispatching:{sender_node} {method}, {arg1}, {arg2}')
        if method == 'successor':
            ###self.log(f'HANDLING (successor): {self.successor}')
            return self.successor
            
        elif hasattr(self, method):
            ###self.log(f'HANDLING ({method})...')
            func = getattr(self, method)
            if arg1 is not None and arg2 is not None:
                return func(arg1, arg2)
            elif arg1 is not None:
                return func(arg1)
            else:
                return func()
        else:
            return 'NoMethodError'


    def call_rpc(self, send_to_node, method, arg1 = None, arg2 = None):
        '''Use TCP and pickle to send a remote procedure call to another node'''
        if arg1 is None and arg2 is None:
            self.log(f'{send_to_node}.{method}()')
        elif arg1 is not None and arg2 is None:
            self.log(f'{send_to_node}.{method}({arg1})')
        elif arg1 is not None and arg2 is not None:
            self.log(f'{send_to_node}.{method}({arg1}, {arg2})')

        ###self.log(f'Call_RPC({send_to_node}, {method}, {arg1}, {arg2})')
        address = ChordNode.lookup_node(send_to_node)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(5)
                s.connect(address)
                s.sendall(pickle.dumps((method, arg1, arg2)))
                result = pickle.loads(s.recv(BUF_SZ))
            except Exception as e:
                print('Error: ', e)
                result = None 
            finally:
                s.close()
        if result != 'NoMethodError':
            #self.log(f"Got RPC RESPONSE {result}")
            self.log(f'\tresult: {result}')
            

            return result
        else:
            raise ValueError('NoMethodError')


    #Data Store Section

    def get_value(self, key):
        print('get_value()')
        hashed_key = hash_key(key)
        if self.is_responsible_for_key(hashed_key):
            # If this node is responsible, return the value
            return self.retrieve_data(key)
        else:
            # Otherwise, route the query to the correct node
            successor = self.find_successor(hashed_key)
            return self.call_rpc(successor, 'get_value', key)

    def put_value(self, key, value):
        hashed_key = hash_key(key)
        print(f"put_value({key}, {value})")
        if self.is_responsible_for_key(hashed_key):
            # If this node is responsible, store the key-value pair locally
            self.store_data(key, value)
            return "Value stored successfully"
        else:
            # Otherwise, route the storage request to the correct node
            successor = self.find_successor(hashed_key)
            return self.call_rpc(successor, 'put_value', key, value)

    def is_responsible_for_key(self, hashed_key):
        """Determine if this node is responsible for a given hashed_key."""
        predecessor = self.call_rpc(self.predecessor, 'get_id')
        return hashed_key in ModRange(predecessor + 1, self.node + 1, NODES)

    def get_id(self):
        return self.node

    def store_data(self, key, value):
        """Store data at this node."""
        self.keys[key] = value
        print(f"Data stored at Node {self.node}: Key = {key}, Value = {value}")

    def retrieve_data(self, key):
        """Retrieve data from this node."""
        value = self.keys.get(key, None)
        print(f"Data retrieved from Node {self.node}: Key = {key}, Value = {value}")
        return value

    def store_data_on_node(port, key, value):
        """RPC to store a key-value pair in the Chord DHT."""
        node_address = ChordNode.lookup_node(port)
        print(f"Storing data: {key} -> {value} on node at port {port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(node_address)
            # Send the RPC to store the key-value pair
            s.sendall(pickle.dumps(('put_value', key, value)))
            # Receive and print the response
            response = pickle.loads(s.recv(BUF_SZ))
            print(f"Response from node: {response}")
            return response
    
    def get_value_from_node(port, key):
        """RPC to query a value for the given key from the Chord DHT."""
        node_address = ChordNode.lookup_node(port)
        print(f"Querying for key: {key} from node at port {port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(node_address)
                # Send the RPC to get the key-value pair
                s.sendall(pickle.dumps(('get_value', key, None)))
                # Receive and print the response
                print('checkpoint1')
                response = pickle.loads(s.recv(BUF_SZ))
                return response
            except Exception as e:
                print(f"Error while querying key: {key} -> {e}")
                return None

    



        
    def log(self, message):
        #print(f'[Node {self.node}]: {message}')
        print(message)
            
    def log_finger_table(self):
        table_entries = [f"{entry.start}: {entry.node}" for i, entry in enumerate(self.finger) if entry]
        self.log(f"Finger Table: {', '.join(table_entries)}")
        self.log(f"Successor: {self.successor}, Predecessor: {self.predecessor}")

    def __str__(self):
        return f'Node[{self.node}]: {self.predecessor}, {self.successor}'
    
    def __repr__(self):
        fingers = ','.join([str(self.finger[i].node) for i in range(1, M+1)])
        return '<{}: [{}]{}>'.format(self.node, fingers, self.predecessor)
        
if __name__ == '__main__':
    #Ensure that input is given
    print(M)
    if len(sys.argv) < 2:
        raise ValueError("Invalid Passed Arguments. Should be \'python chord_node.py node_port network_port\'")
    else:
        #get the port number for the network
        node_id = int(sys.argv[1])
        if len(sys.argv) > 2:
            known_node_id = int(sys.argv[2])
        else:
            known_node_id = 0
        
        node1 = ChordNode(2)
        node2 = ChordNode(1, 2)
        node3 = ChordNode(5, 1)
        node4 = ChordNode(0, 2)
        

        
        while(True):
            pass
