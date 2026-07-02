from mysite.tenant_context import get_current_db_name

class MasterTenantRouter:
    MASTER_APPS = {'admin', 'auth', 'contenttypes', 'sessions', 'knox', 'register'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.MASTER_APPS:
            return 'default'
        # Return the currently active tenant database from the thread context
        return get_current_db_name() or 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.MASTER_APPS:
            return 'default'
        return get_current_db_name() or 'default'
    
    def allow_migrate(self, db, app_label, **hints):
        if app_label in self.MASTER_APPS:
            return db == 'default'
        
        # Fallback: if get_current_db_name() is None, 
        # check if the database being migrated is one of our known tenant names
        current_db = get_current_db_name()
        if current_db:
            return db == current_db
        return None