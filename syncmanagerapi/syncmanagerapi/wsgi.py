from .settings import import_entry_point
# only run this file in production environment
entry_point = import_entry_point('create_app')
app = entry_point()
