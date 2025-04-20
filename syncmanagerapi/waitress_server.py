from .settings import import_entry_point

entry_point = import_entry_point('create_app')
serve(entry_point(), host='127.0.0.1', port=5000)
