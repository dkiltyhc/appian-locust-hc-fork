import errno
import json
import os

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
FOLDER_NAME = 'mocks'


def read_mock_file(file_name: str) -> str:
    path_to_file = os.path.join(DIR_PATH, FOLDER_NAME, file_name)
    if os.path.exists(path_to_file):
        with open(path_to_file) as f:
            return f.read()
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path_to_file)


def read_mock_file_as_dict(file_name: str) -> dict:
    file_text = read_mock_file(file_name)
    return json.loads(file_text)
