import os.path as osp;

def get_root_directory():
    dir = osp.dirname(osp.realpath(__file__))
    return osp.dirname(dir)
