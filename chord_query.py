import sys
import pickle
import socket
from chord_node import ChordNode, hash_key, BASE_PORT, BUF_SZ




if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python chord_query.py [node_port] [player_id] [year]")
        print("Example: ")
        key = ('tomfarris/2513861', 1947)
        print("python chord_query.py {} {} {}".format(BASE_PORT, key[0], key[1]))
        print()
    else:
        port = int(sys.argv[1])
        key = f"{sys.argv[2]}/{sys.argv[3]}"  # Create the key as 'player_id/year'

    value = ChordNode.get_value_from_node(port, key)
    if value:
        print(f"Value for key {key}: {pickle.loads(value)}")
    else:
        print(f"Key {key} not found in the network.")