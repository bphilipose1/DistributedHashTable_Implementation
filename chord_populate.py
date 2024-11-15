import sys
import pickle
import socket
import hashlib
import csv
import os
from chord_node import ChordNode

'''

def store_data_on_node(port, key, data):
    # Connect to the node and send data using RPC
    address = ('localhost', port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(address)
        s.sendall(pickle.dumps(('store_key_value', key, data)))
        response = pickle.loads(s.recv(BUF_SZ))
        return response

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python chord_populate.py [node_port] [filename]")
        sys.exit(1)
    
    node_port = int(sys.argv[1])
    filename = sys.argv[2]

    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            player_id, year = row[0], row[3]
            key = int(f"{player_id}{year}")
            hashed_key = hash_key(key)
            data = row[1:]  #store other columns as data
            store_data_on_node(node_port, hashed_key, data)'''
            

def populate_from_qb(port, filename, rows=None):
    node = ChordNode.lookup_addr(port)
    print(f"Populating data from {filename} starting at node {node}")

    with open(filename, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)  # Skip header row

        count = 0
        for row in csvreader:
            player_id = row[0]
            year = int(row[3])
            stat_value = row  # All columns as the value
            key = f"{player_id}/{year}"
            value = pickle.dumps(stat_value)

            # Store in the Chord network
            ChordNode.store_data_on_node(port, key, value)

            count += 1
            if rows and count >= rows:
                break


            
if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print("Usage: python chord_populate.py [node_port] [filename] [MAX_ROWS]")
        print("Example: ")
        port = 31488
        filename = 'Career_Stats_Passing.csv'
        rows = 10
        print("python chord_populate.py {} {} {}".format(port, filename, rows))
        print()
    else:
        print(sys.argv)
        port = int(sys.argv[1])
        filename = os.path.expanduser(sys.argv[2])
        rows = None if len(sys.argv) < 3 else int(sys.argv[3])
        
    populate_from_qb(port, filename, rows)