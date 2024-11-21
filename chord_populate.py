import sys
import pickle
import csv
import os
from chord_node import ChordNode

def populate_from_qb(port, filename, rows=None):
    """Populate the Chord network with data from a CSV file

    Args:
        port (Int): Port number to start the Chord network on
        filename (String): Path to the CSV file to populate from
        rows (Int, optional): Number of Rows to insert in to DHT from CSV. Defaults to None.
    """
    print(f"Populating data from {filename} starting at port {port}")

    with open(filename, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)  #skip header row

        count = 0
        for row in csvreader:
            player_id = row[0]
            year = int(row[3])
            stat_value = row  #all columns as the value
            key = f"{player_id}/{year}"
            value = pickle.dumps(stat_value)

            #store in the Chord network
            address = ('localhost', port)
            ChordNode.store_data_on_node(address, key, value)

            count += 1
            if rows and count >= rows:
                break


            
if __name__ == '__main__':
    """Populate the Chord network with data from a CSV file"""
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
        
    populate_from_qb(port, filename, rows + 1)