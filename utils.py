import os


def file_or_dir_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False
