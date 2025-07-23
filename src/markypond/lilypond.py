"""
Lilypond interface.

"""
import os
import subprocess
import logging

from .exceptions import MarkypondError
from .utils import mkdirs_for_path

LILYPOND_LOGLEVEL = 'BASIC'

logger = logging.getLogger(__name__)


def run_lilypond(src, path):
    """
    Call the lilypond command line tool as a subprocess.

    Missing directories in the provided path will be created on the fly, and
    the desired format will be deduced from the file extension.

    Raises a MarkypondError if lilypond returns anything other than 0.
    """
    mkdirs_for_path(path)

    if os.path.exists(path):
        logger.info('Skipping lilypond generation: cache file already exists.')
        return

    path, fmt = os.path.splitext(path)
    fmt = fmt.lstrip('.')
    result = subprocess.run(
        ['lilypond',
         f'-f{fmt}',
         f'--loglevel={LILYPOND_LOGLEVEL}',
         '-dno-point-and-click',
         '-o', path, '-'],
        input=src,
        text=True,
        capture_output=True)
    if result.returncode != 0:
        raise MarkypondError(
            "Something went wrong when running lilypond. "
            "Lilypond output:\n" + result.stderr)
