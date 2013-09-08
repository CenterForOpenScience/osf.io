import os, random, string

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

def random_string(length=8, chars=string.letters+string.digits):
    return ''.join([chars[random.randint(0, len(chars)-1)] for i in range(length)])
