import DEBUG
from StaticActions import StaticActions
import message as msg
from constants import *

class MessageAction:

    def __init__( self, database, send_message_func, get_client_list_func, get_client_func, game_inst=None ):
        # self.game_inst = game_inst
        self.database = database
        self.send_message = send_message_func
        self.get_client_list = get_client_list_func
        self.get_client = get_client_func
        self.game_inst = game_inst



    def run( self, message_obj ):
        """

        :param message_obj: instance of messages containing the data
        :return: None
        """
        pass


class Action_SendMessage( MessageAction ):  # m

    def run( self, message_obj ):

        clients = self.get_client_list( [message_obj.from_client_key] )
        message_obj.to_clients = clients

        self.send_message( message_obj )
        DEBUG.DEBUG.print("Sending message")


class Action_ClientIdentity( MessageAction ):   # i

    def run( self, message_obj ):

        connection = self.get_client( message_obj.from_client_key )

        nickname = message_obj["nickname"]
        reg_key = message_obj["reg_key"]

        # make sure that the users has set a nick name
        if not nickname.string():
            StaticActions.send_server_status( False, "No username", client.key, SERVER_NAME,
                                              self.send_message )
            return

        # if they have a reg key find if they where connected to a lobby or game
        if reg_key.strip():
            pass
        else:   # reg the user :)
            connection.client_key, reg_key = self.database.add_new_client(nickname)


        StaticActions.send_server_status(True, "", client.key, SERVER_NAME,
                                         self.send_message)


class Action_status( MessageAction ):

    TYPE_NONE   = -1
    TYPE_SERVER = 0
    TYPE_CLIENT = 1
    TYPE_GAME   = 2

    def run ( self, messageObj ):
        pass

class Action_GamesRequest( MessageAction ): # g

    def run( self, message_obj ):

        # fill in the game names and slots data and send the class back to the client
        games = self.get_games()

        game_names = []
        game_slots = []

        for g in games:
            game_names.append( g.game.game_name )
            game_slots.append( str(g.game.max_players - g.get_player_count()) + " of " + str(g.game.max_players) )

        message_obj.to_clients = [message_obj.from_client_key]
        message_obj.message["available_games"] = game_names
        message_obj.message["available_slots"] = game_slots

        self.send_message( message_obj )

class Action_JoinLobbyRequest( MessageAction ): # j

    def run( self, message_obj ):

        games = self.get_games(False)
        client = self.get_client( message_obj.from_client_key )
        joined = False

        for g in games:
            if g.game.game_name == message_obj["match_name"]:
                # attempt to join game
                if g.can_join():
                    joined = client.set_active_game(g)

                if joined:
                    # let the player knows every thing is ok
                    StaticActions.send_game_status(True, "", message_obj.from_client_key,
                                                   SERVER_NAME, self.send_message)
                    # notify the other players that they have connected
                    StaticActions.send_client_status( True, "", client.key, client.name,
                                                      self.get_client_list, self.send_message, g )
                    # send the initial game data to the client.
                    StaticActions.send_game_info(g, message_obj.from_client_key,
                                                 SERVER_NAME, self.send_message)
                else:
                    StaticActions.send_game_status( False, self.get_error_message(g, client),
                                                    message_obj.from_client_key,
                                                    SERVER_NAME, self.send_message )
                return

            # its not ok, the game is no longer exist!
            StaticActions.send_game_status( False, "Game does not exist!", message_obj.from_client_key,
                                            SERVER_NAME, self.send_message )


    def get_error_message( self, game, client ):

        err_msg = ""
        if game.game_active:
            err_msg = "Game has already started"
        elif game.get_available_slots() < 1:
            err_msg = "Server is full"
        elif client.get_active_game() is not None:
            err_msg = "Client is already in an active game"

        return err_msg

class Action_JoinedGame( MessageAction ):

    def run( self, message_obj ):

        # send to all other players
        from_client = self.get_client(message_obj.from_client_key)
        game = from_client.get_active_game()

        if game is None:
            DEBUG.DEBUG.print( "{0} ({1}) can not join game, not in lobby".format(from_client.key, from_client.name),
                               message_type=DEBUG.DEBUG.MESSAGE_TYPE_ERROR )
            return;

        message_obj.to_clients = self.get_client_list( [from_client.key], game )

        game.player_joined( message_obj.from_client_key, message_obj["player_id"] )


class Action_StartGame( MessageAction ):

    def run( self, message_obj ):

        # ready the player
        from_client = self.get_client( message_obj.from_client_key )
        game = from_client.get_active_game()

        game.ready_player( message_obj.from_client_key, message_obj["ok"])
