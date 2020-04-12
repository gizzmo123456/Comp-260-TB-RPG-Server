import threading
import time


class Task:

    def __init__( self,):
        self.task_id = -1
        self.stop = False

    def new_task( self, message_obj, delay, complete_func ):
        """ starts a new task

        :param message_obj:     message that to sent
        :param delay:           delay until the message is send
        :param complete_func:   callback function when task in complete must has int param for task id
        :return:                new task id
        """
        if self.stop:
            return -1

        self.task_id += 1
        thr = threading.Thread( target=self.task,
                                args=(self.task_id, message_obj, delay, complete_func) )
        thr.start()

        return self.task_id

    def stop( self ):
        self.stop = True

    def task( self, task_id, message_obj, delay, complete_func):

        time.sleep( delay )
        if self.stop:
            return

        message_obj.send_message()
        complete_func(task_id)
