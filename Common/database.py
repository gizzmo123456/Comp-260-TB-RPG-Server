import Common.sql_query as sql
import hashlib
import time
import Common.DEBUG as DEBUG
import random

class Database:

    def __init__( self ):

        # make sure that the database has been set up
        self.database = sql.sql_query("tb_rpg", True)

        DEBUG.LOGS.print( "Database Inited Successfully!" )

    def add_new_client( self, nickname ):
        """
            Adds a new client
        :return:    tuple of the client id and reg_id tuple(cid, rid)
        """

        reg_key = hashlib.sha224("{0}{1}".format( nickname, time.time() ).encode() ).hexdigest()

        self.database.insert_row("active_users", ["nickname", "reg_key"], [nickname, reg_key])
        uid = self.database.select_from_table( "active_users", ["uid, reg_key"], ["reg_key"], [reg_key] )[0][0]

        client_id = uid

        return client_id, reg_key

    def get_random_name( self ):

        rand = random.random()
        query = "SELECT word FROM {0} WHERE id >= {1} * (SELECT MAX(id) FROM {0})"
        adj = self.database.execute( query.format( "names_list_adjective", rand ), [] )[0][0]

        rand = random.random()
        noun = self.database.execute( query.format( "names_list_nouns", rand ), [] )[0][0]

        return adj[0:1].upper() + adj[1:].lower() + " " + noun[0:1].upper() + noun[1:]

    def select_client( self, reg_key ):
        """
            Selects users by there reg key
        :param reg_key: the users reg key
        :return:        if found the clients id and nickname otherwise None
        """

        user_data = self.database.select_from_table("active_users", ["uid", "nickname"], ["reg_key"], [reg_key])

        # if theres more than one result somethings gone wrong
        # remove both from the active users list
        if len(user_data) > 1:
            self.database.remove_row("active_users", ["reg_key"], [reg_key])
            DEBUG.LOGS.print("Multiple reg keys found", user_data, message_type=DEBUG.LOGS.MSG_TYPE_FATAL)
            return None
        elif len(user_data) == 0:
            return None

        return user_data[0]

    def update_client_nickname( self, reg_key, nickname ):

        self.database.update_row("active_users",
                                 ["nickname"], [nickname],
                                 ["reg_key"],  [reg_key] )

    def add_new_lobby( self ):

        self.database.insert_row("lobbies", ["level_id"], ["1"])    # TODO: this should just select a level at random.

    def available_lobby_count( self ):

        return self.database.select_from_table("lobbies", ["COUNT(game_id)"], ["game_id<"], ["0"], override_where_cols=True)[0][0]

    def select_all_available_lobbies( self ):
        """

        :return: (tuple) (list (a row) of tuples (the columns), list of current players)
                        [(lobby id, level name, min players, max players), ...],
                        [current_players]...
        """
        query = "SELECT lobbies.uid, levels.uid, levels.name, levels.min_players, levels.max_players" \
                " FROM lobbies JOIN levels ON lobbies.level_id=levels.uid WHERE lobbies.game_id < 0"

        # stitch the current_players count
        lobbies = self.database.execute(query, [])
        current_players = []

        for l in lobbies:
            current_players.append( self.get_lobby_player_count( l[0] ) )

        return lobbies, current_players

    def get_lobby_player_count( self, lobby_id ):

        return self.database.select_from_table("active_users", ["COUNT(lobby_id)"], ["lobby_id"], [lobby_id])[0][0]

    def join_lobby( self, client_id, lobby_id ):
        """ Joins game lobby

        :return: True if successful otherwise False
        """

        # check that the user can join the lobby
        query = "SELECT levels.max_players " \
                "FROM lobbies JOIN levels ON lobbies.level_id = levels.uid " \
                "WHERE lobbies.game_id < 0 AND lobbies.uid = %s"

        lobby = self.database.execute( query, [lobby_id] )
        current_players = self.get_lobby_player_count( lobby_id )

        if len(lobby) != 1:  # error not found
            return  # TODO: send error

        if current_players < lobby[0][0]:
            self.database.update_row( "active_users", ["lobby_id"], [lobby_id], ["uid"], [client_id] )

