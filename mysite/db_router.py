from mysite.tenant_context import get_current_db_name

class MasterTenantRouter:
    # Explicitly route central core business modules to the main hub registry
    MASTER_MODELS = {'company_register', 'register_employee'}
    MASTER_APPS = {'admin', 'auth', 'contenttypes', 'sessions', 'knox', 'register'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.MASTER_APPS or model._meta.model_name in self.MASTER_MODELS:
            return 'default'
        return get_current_db_name()

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.MASTER_APPS or model._meta.model_name in self.MASTER_MODELS:
            return 'default'
        return get_current_db_name()

    def allow_relation(self, obj1, obj2, **hints):
        obj1_master = obj1._meta.app_label in self.MASTER_APPS
        obj2_master = obj2._meta.app_label in self.MASTER_APPS
        if obj1_master == obj2_master:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.MASTER_APPS or model_name in self.MASTER_MODELS:
            return db == 'default'
        return None