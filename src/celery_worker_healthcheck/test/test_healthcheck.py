from time import sleep
import contextlib
import importlib.resources
import socket
import subprocess
import sys

import pytest
import requests
import requests.exceptions


def random_port():
    s = socket.socket()
    with contextlib.closing(s):
        s.bind(('localhost', 0))
        return s.getsockname()[1]


@pytest.fixture()
def server(tmp_path):
    port = random_port()

    config = importlib.resources.files(__package__).joinpath('fixture/conf.py').open('r').read()
    (tmp_path / 'celeryconfig.py').write_text(config.format(port=port))
    proc = subprocess.Popen(
        [
            sys.executable,
            '-m',
            'celery',
            '--app=celery_worker_healthcheck.test.fixture.app.CELERY',
            # XXX This is the default, but is not used if not set explicitly.
            '--config=celeryconfig',
            'worker',
            '--concurrency=2',
        ],
        cwd=str(tmp_path),
    )
    yield port
    proc.terminate()
    proc.wait(5)


def test_runs_healthcheck_on_separate_port(server):
    http = requests.Session()
    timeout = 10
    for _ in range(timeout):
        sleep(1)
        try:
            r = http.get(f'http://localhost:{server}')
            if r.status_code == 200:
                assert r.text.strip() == '2 workers ready'
                break
        except requests.exceptions.ConnectionError:
            pass
    else:
        pytest.fail(f'Did not start inside {timeout} seconds')
