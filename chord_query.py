import sys
import pickle
import socket
import sys
from chord_node import ChordNode, hash_key, BASE_PORT



if len(sys.argv) != 4:
    print("Usage: python chord_query.py [node_port] [player_id] [year]")
    print("Example: ")
    #key = ('russellwilson/2532975', 2016)
    key = ('tomfarris/2513861', 1947)
    print("python chord_query.py {} {} {}".format(BASE_PORT, key[0], key[1]))
    print()
else:
    port = int(sys.argv[1])
    key = (sys.argv[2], int(sys.argv[3]))
    
node = ChordNode.lookup_addr(port)
print('looking up key:', key, 'from node:', node)
print(ChordNode.get_value(node, key))    
