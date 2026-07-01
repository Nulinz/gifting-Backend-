from mysite.tenant_context import get_current_db_name

class MasterTenantRouter:
    MASTER_APPS = {'admin', 'auth', 'contenttypes', 'sessions', 'knox', 'register'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.MASTER_APPS:
            return 'default'
        return 'tenant' # Always route to the proxy

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.MASTER_APPS:
            return 'default'
        return 'tenant' # Always route to the proxy
    
    def allow_migrate(self, db, app_label, **hints):
        if app_label in self.MASTER_APPS:
            return db == 'default'
        return db == 'tenant' # Only allow migrations on the tenant proxy