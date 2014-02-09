import os

def get_module_dirs(modules_dir):
    modules_dir = modules_dir.replace('/', '')
    return [f for f in os.listdir(modules_dir) if os.path.isdir(os.path.join(modules_dir, f))]

def get_directories(directory):
    if not isinstance(directory, list):
        directory = [directory]
    res = []
    for i in directory:
        for root, dirs, files in os.walk(i):
            res.append(os.path.join(os.getcwd(), str(root)))
    return res
