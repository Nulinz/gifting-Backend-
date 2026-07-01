import threading

_thread_local = threading.local()

def set_current_db_name(db_name):
    _thread_local.CURRENT_DB = db_name

def get_current_db_name():
    return getattr(_thread_local, 'CURRENT_DB', 'default')

def clear_current_db_name():
    _thread_local.CURRENT_DB = 'default'