import click, os, sys, shutil

import tarfile

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

if os.name == 'posix' and sys.version_info[0] < 3:
    import urllib
else:
    import urllib.request as urllib

def is_string(obj):
    return isinstance(obj, basestring)

def as_bytes(s):
    if sys.version_info[0] < 3: return bytes(s)
    else: return bytes(s, "UTF-8")

def as_string(x):
    if x is None: return ''
    elif sys.version_info[0] < 3: return str(x)
    else: return str(x, encoding="UTF-8")

class BuildError(Exception):
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        if None: return "Build failed"
        else: return self.msg

def try_until(*args):
    for arg in args:
        try: 
            arg()
            return
        except:
            pass
    raise BuildError()

def write_to(file, lines):
    content = list((line + "\n" for line in lines))
    if (len(content) > 0):
        open(file, 'w').writelines(content)

def mkdir(p):
    if not os.path.exists(p): os.makedirs(p)
    return p
    
def mkfile(d, file, content, always_write=True):
    mkdir(d)
    p = os.path.join(d, file)
    if not os.path.exists(p) or always_write:
        write_to(p, content)
    return p

def lsdir(p):
    if os.path.exists(p):
        return (d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)))
    else:
        return []

def symlink_dir(src, dst):
    for root, dirs, files in os.walk(src):
        for file in files:
            path = os.path.relpath(root, src)
            d = os.path.join(dst, path)
            mkdir(d)
            os.symlink(os.path.join(root, file), os.path.join(d, file))

def rm_symlink(file):
    if os.path.islink(file):
        f = os.readlink(file)
        if not os.path.exists(f): os.remove(file)

def rm_symlink_dir(d):
    for root, dirs, files in os.walk(d):
        for file in files:
            rm_symlink(os.path.join(root, file))

def rm_empty_dirs(d):
    has_files = False
    for x in os.listdir(d):
        p = os.path.join(d, x)
        if os.path.isdir(p): has_files = has_files or rm_empty_dirs(p)
        else: has_files = True
    if not has_files: os.rmdir(d)
    return has_files

def get_dirs(d):
    return (os.path.join(d,o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o)))

def copy_to(src, dst_dir):
    target = os.path.join(dst_dir, os.path.basename(src))
    if os.path.isfile(src): shutil.copyfile(src, target)
    else: shutil.copytree(src, target)
    return target

def download_to(url, download_dir):
    name = url.split('/')[-1]
    file = os.path.join(download_dir, name)
    click.echo("Downloading {0}".format(url))
    with click.progressbar(length=100) as bar:
        def hook(count, block_size, total_size):
            percent = int(count*block_size*100/total_size)
            if percent > 0 and percent < 100: bar.update(percent)
        urllib.urlretrieve(url, filename=file, reporthook=hook, data=None)
    return file

def retrieve_url(url, dst):
    if url.startswith('file://'): return copy_to(url[7:], dst)
    else: return download_to(url, dst)

def extract_ar(archive, dst):
    tarfile.open(archive).extractall(dst)

def which(p):
    for dirname in os.environ['PATH'].split(os.pathsep):
        candidate = os.path.join(os.path.expanduser(dirname), p)
        if os.path.exists(candidate):
            return candidate
    raise BuildError("Can't find file %s" % p)

def cmd(args, env={}, **kwargs):
    e = dict(os.environ)
    e.update(env)
    child = subprocess.Popen(args, env=e, **kwargs)
    child.communicate()
    if child.returncode != 0: raise BuildError("Error: " + str(args))

def cmake(args, cwd=None, toolchain=None, env=None):
    if toolchain is not None: args.insert(0, '-DCMAKE_TOOLCHAIN_FILE={0}'.format(toolchain))
    cmd([which('cmake')]+args, cwd=cwd, env=env)


def pkg_config(args, path=None):
    env = {}
    if path is not None: env['PKG_CONFIG_PATH'] = path
    cmd([which('pkg-config')]+list(args), env=env)

