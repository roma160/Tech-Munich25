import pathlib

def get_root_folder():
    return pathlib.Path(__file__).parent.absolute()