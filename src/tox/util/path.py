import logging
import shutil


def ensure_empty_dir(path):
    if path.check():
        logging.warning(f"  removing {path}")
        shutil.rmtree(str(path), ignore_errors=True)
        path.ensure(dir=1)
