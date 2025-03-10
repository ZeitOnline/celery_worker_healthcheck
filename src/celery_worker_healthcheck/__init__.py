from glob import glob
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
import logging
import os
import threading

import celery.signals


__version__ = '1.1.0.dev0'


def start(sender, *args, **kw):
    conf = sender.app.conf
    bind = conf.get('worker_healthcheck_bind')
    if not bind:
        return

    check = HealthCheck(
        bind,
        conf.get('worker_healthcheck_directory', ''),
        conf.get('worker_healthcheck_filename', '.celery.worker.{}'),
        conf.get('worker_healthcheck_minimum', 1),
    )
    check.register()
    check.start()


class HealthCheck(threading.Thread):
    def __init__(self, bind, directory, filename, minimum):
        self.bind = bind
        self.directory = directory
        self.filename = filename
        self.minimum = minimum

        WSGIRequestHandler.log_request = lambda *args: None  # sigh
        host, port = self.bind.split(':')
        self.server = WSGIServer((host, int(port)), WSGIRequestHandler)
        self.server.set_app(self.wsgi_app)

        logging.getLogger('celery').info('Healthcheck listening at: http://%s', self.bind)
        super().__init__(daemon=True, target=self.server.serve_forever)

    def register(self):
        celery.signals.worker_process_init.connect(weak=False)(self.add_worker)
        celery.signals.worker_process_shutdown.connect(weak=False)(self.remove_worker)
        celery.signals.worker_shutdown.connect(weak=False)(self.stop)

    def add_worker(self, *args, **kw):
        open(self.pidfile(os.getpid()), 'w').close()

    def remove_worker(self, *args, **kw):
        f = self.pidfile(os.getpid())
        if os.path.exists(f):
            os.remove(f)

    def pidfile(self, name):
        return os.path.join(self.directory, self.filename.format(name))

    def stop(self, *args, **kw):
        for f in glob(self.pidfile('*')):
            os.remove(f)

        self.server.shutdown()
        self.server.server_close()
        self.join(1)

    def wsgi_app(self, environ, start_response):
        count = len(list(glob(self.pidfile('*'))))
        if count >= self.minimum:
            status = '200 OK'
        else:
            status = '500 Internal Server Error'
        start_response(status, [('Content-type', 'text/plain; charset=ascii')])
        return [f'{count} workers ready\n'.encode('ascii')]
