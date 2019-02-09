import os
import sys

try:
    from syncmanagerapi import main
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from syncmanagerapi import main

if __name__ == '__main__':
    main()
