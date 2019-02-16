from .settings import import_entry_point

entry_point = import_entry_point('create_app')
app = entry_point()
