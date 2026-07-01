import threading

_thread_locals = threading.local()

def set_current_db_name(db_name):
    """Saves the database name, cleanly forcing spaces to underscores."""
    if db_name:
        clean_name = db_name.strip().replace(" ", "_")
        setattr(_thread_locals, 'db_name', clean_name)
    else:
        setattr(_thread_locals, 'db_name', 'default')

def get_current_db_name():
    """Retrieves the active thread-local database target configuration name."""
    return getattr(_thread_locals, 'db_name', 'default')

def clear_current_db_name():
    """Clears thread memory context at the end of a request lifecycle."""
    if hasattr(_thread_locals, 'db_name'):
        delattr(_thread_locals, 'db_name')