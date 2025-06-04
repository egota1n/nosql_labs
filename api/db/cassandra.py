from cassandra.cluster import Cluster
import os

cluster = Cluster([os.getenv("CASSANDRA_HOST", "127.0.0.1")])
session = cluster.connect("airport")

def get_cassandra_session():
    return session