# test server (to test passthroug connection)
import socket
import Common.database as database
import Common.Globals as Global
import Common.DEBUG as DEBUG
import time

print = DEBUG.LOGS.print    # override python print with my own.
config = Global.GlobalConfig

Global.setup()

host = config.get("internal_host") # socket.gethostname() # "DESKTOP-S8CVUEK"
port = 8223

connected = False

DEBUG.LOGS.init()
DEBUG.LOGS.set_log_to_file(error=False)

db = database.Database()

# what for sql to come online
while not db.database.test_connection():
    time.sleep( 3 )  # try every 10 seconds

time.sleep( 1.1 )  # we'll just wait a lil longer befor adding to the db


db.database.insert_row("games", ["available", "host"], [True, host])
print (">-----", db.database.select_from_table( "games", ["host"] ) )

active_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
active_socket.bind( (host, port) )
active_socket.listen( 99 )

while not connected:
    print("waiting for connections @ ", (host, port))
    client_sock, addr = active_socket.accept()
    print( "client accepted @ ", addr )
    connected = True

print("waiting to receive")
while True:
    try:
        data = client_sock.recv(100)
        print (data)
        client_sock.send(data)
    except Exception as e:
        print ("failed", e)
