class TenantRouter:
    # Models that live ONLY in the Master Registry
    master_models = {'CompanyRegistry'}

    def db_for_read(self, model, **hints):
        if model.__name__ in self.master_models:
            return 'default'
        return 'tenant'

    def db_for_write(self, model, **hints):
        if model.__name__ in self.master_models:
            return 'default'
        return 'tenant'

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # The model being migrated
        model = hints.get('model')
        model_name_str = model.__name__ if model else model_name

        # 1. Master DB: Only allow Master Models
        if db == 'default':
            return model_name_str in self.master_models

        # 2. Tenant DB: Block Master Models, allow EVERYTHING else
        if db == 'tenant':
            if model_name_str in self.master_models:
                return False  
            return True      

        return None