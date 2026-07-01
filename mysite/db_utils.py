from django.conf import settings
from django.db import connections

def connect_to_db(db_name):
    # If the database is already known, do nothing
    if db_name in connections.databases:
        return
    
    # If it's new, add it to Django's memory dynamically
    db_config = settings.DATABASES['default'].copy()
    db_config['NAME'] = db_name
    connections.databases[db_name] = db_config
    connections.configure_settings(settings.DATABASES)