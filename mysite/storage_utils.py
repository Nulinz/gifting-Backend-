
from mysite.tenant_context import get_current_db_name

def get_employee_image_path(instance, filename):
    # This safely retrieves the current database name to use as a folder prefix
    company_folder = get_current_db_name() or "default"
    return f"{company_folder}/employees/{instance.employee_id}/{filename}"