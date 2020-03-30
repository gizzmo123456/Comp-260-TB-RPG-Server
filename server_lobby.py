import Common.DEBUG as DEBUG
import Common.database as db
import Sockets.ServerLobbySocket as ServerLobbySocket
import Sockets.SocketHandler as SocketHandler
import Common.constants as const
import Common.message as message
import Common.actions
import time
import Common.Protocols.status as statusProtocols
import os
import Common.Globals as Global
config = Global.GlobalConfig

GAME_START_TIME = 30        # seconds until the game can start once there is enough players
NEW_PLAYER_DELAY = 10

def process_connections( conn ):
    # process any messages from the client
    while conn.receive_message_pending():
        conn.receive_message().run_action()


def clean_lobby( connection ):

    lobby_id = connection.lobby_id
    client_nickname = connection.client_nickname
    # remove the client from the lobby
    if lobby_id in lobbies and connection.socket in lobbies[lobby_id]:
        del lobbies[lobby_id][connection.socket]

        # notify all the others that a client has left.
        msg = message.Message( 'm' )
        msg.new_message( client_nickname, [ ], "Has Left the Server :( " )
        msg.to_connections = get_lobby_connections( lobby_id )
        msg.send_message()

        send_client_list( lobby_id )

        send_lobby_info( lobby_id )


def process_client_identity( message_obj ):

    DEBUG.LOGS.print( "Recivedd id", message_obj[ "client_id" ], message_obj[ "reg_key" ] )

    from_conn = message_obj.from_connection

    # add the clients data to the connection
    from_conn.set_client_key( message_obj[ "client_id" ], message_obj[ "reg_key" ] )

    # find the user in the database and make sure they have arrived at the correct location
    client_info = database.select_client( message_obj[ "reg_key" ] )
    client_nickname = client_info[1]
    client_lobby_id = client_info[2]

    # find if the lobby exist on the server
    # if not double check that the client has arrive at the correct location
    # and create a new lobby.
    if client_lobby_id in lobbies:
        lobbies[ client_lobby_id ][ from_conn.socket ] = from_conn
    else:
        host = database.get_lobby_host( client_lobby_id )
        if host == config.get("internal_host"):
            lobbies[ client_lobby_id ] = { from_conn.socket: from_conn }
            lobbies_start_times [ client_lobby_id ] = -1
        else:   # it appears the clients has arrived at the wrong location.
            DEBUG.LOGS.print( "Client has arrived at the wrong lobby host. expected:", config.get("internal_host"), "actual", host, "Disconnecting...",
                              message_type=DEBUG.LOGS.MSG_TYPE_FATAL )

            from_conn.safe_close()
            return

    # update the connection with the db data
    from_conn.lobby_id = client_lobby_id
    from_conn.client_nickname = client_nickname

    # send all the clients an updated list of connected clients
    send_client_list( client_lobby_id )

    # let everyone know you have joined
    msg = message.Message('m')
    msg.new_message(client_nickname, [], "Has Joined the Server :D Yay! ")
    msg.to_connections = get_lobby_connections(client_lobby_id)
    msg.send_message()

    # send start status
    send_lobby_info( client_lobby_id )


def process_message( message_obj ):

    # TODO: filter out connections that are not in to conn
    message_obj["from_client_name"] = message_obj.from_connection.client_nickname
    message_obj.to_connections = get_lobby_connections( message_obj.from_connection.lobby_id )
    message_obj.send_message()


def send_lobby_info(lobby_id):

    level_name, min_players, max_players = database.get_lobby_info( lobby_id )

    # set/unset the game start time as required
    if lobbies_start_times[ lobby_id ] < 0 and get_clients_in_lobby( lobby_id ) >= min_players:
        lobbies_start_times[ lobby_id ] = time.time() + GAME_START_TIME
    elif lobbies_start_times[ lobby_id ] > 0 and get_clients_in_lobby( lobby_id ) < min_players:
        lobbies_start_times[ lobby_id ] = -1
    elif lobbies_start_times[ lobby_id ] > 0:  # add a little more time if a new player connects.
        lobbies_start_times[ lobby_id ] += NEW_PLAYER_DELAY

    lobby_info = message.Message( 'O' )
    lobby_info.new_message( const.SERVER_NAME, level_name, min_players, max_players, lobbies_start_times[ lobby_id ] - time.time() )
    lobby_info.to_connections = get_lobby_connections( lobby_id )
    lobby_info.send_message()


def send_client_list( lobby_id ):

    cids, nnames = database.get_lobby_player_list( lobby_id )
    connected_clients = message.Message('C')
    connected_clients.new_message(const.SERVER_NAME, cids, nnames)
    connected_clients.to_connections = get_lobby_connections( lobby_id )
    connected_clients.send_message()


def get_lobby_connections( lobby_id ):
    """gets the list of connections in lobby"""

    if lobby_id in lobbies:
        return list( lobbies[lobby_id].values() )


def get_clients_in_lobby( lobby_id ):

    if lobby_id in lobbies:
        return len( lobbies[lobby_id] )


if __name__ == "__main__":

    running = True
    lobby_host_id = -1

    # the lobbies that exist on this host.
    lobbies = {}    # key = lobby id in db, value is dict of lobby connections key socket, value connection
    lobbies_start_times = {} # key = lobby id value if > 0 start time else not enough players

    # set up
    Global.setup()

    DEBUG.LOGS.init()
    DEBUG.LOGS.set_log_to_file(message=True, warning=True, error=True, fatal=True)

    database = db.Database()

    # register the host into the database
    # wait for the sql server to come online
    while not database.database.test_connection():
        time.sleep(5)

    lobby_host_id = database.add_lobby_host( config.get( "internal_host" ) )

    # bind message functions
    message.Message.bind_action( '&', Common.actions.processes_ping )
    message.Message.bind_action( 'i', process_client_identity )
    message.Message.bind_action( 'm', process_message )

    # setup socket and bind to accept client socket
    port = config.get( "internal_port" )
    socket_handler = SocketHandler.SocketHandler( config.get( "internal_host" ), port,
                                                  15, ServerLobbySocket.ServerLobbySocket )

    socket_handler.start()

    # Welcome the server
    DEBUG.LOGS.print("Welcome", config.get("internal_host"), ":", config.get("internal_port"), " - Your host id is: ", lobby_host_id )

    while running:

        socket_handler.process_connections( process_func=process_connections, extend_remove_connection_func=clean_lobby )

        for st in lobbies_start_times:
            if st > 0 and time.time() > st:
                # start the lobby
                pass

    database.remove_lobby_host( config.get( "internal_host" ) )
