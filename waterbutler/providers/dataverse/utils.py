import os


# For use in determining which version of a file was just uploaded
def unpack_filename(filename):
    basename, ext = os.path.splitext(filename)
    version = 0
    if basename.rsplit('-', 1)[-1].isdigit():
        basename, version = basename.rsplit('-', 1)

    return basename + ext, int(version)