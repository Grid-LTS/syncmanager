import os
import sys


def import_entry_point(function_name):
    try:
        import syncmanagerapi
    except ImportError:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import syncmanagerapi
    return getattr(syncmanagerapi, function_name)
