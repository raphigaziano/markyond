"""
Misc utils

"""
import os


def mkdirs_for_path(path):
    """ Create missing directories from `path` of those are missing. """
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))


# from https://stackoverflow.com/a/11326230
# fix shenanigans with urllib.parse.urljoin, which remove parts of the leading
# fragment if it doesn't end with a slash.
def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """

    return "/".join(map(lambda x: str(x).rstrip('/'), args))
