# celery_worker_healthcheck

HTTP endpoint that counts ready celery workers

The main usecase is configuring this as a Kubernetes [readinessProbe](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/).
If a faulty software update is deployed that prevents the worker from starting,
the `readinessProbe` detects this, and keeps the previously running Pods,
instead of replacing them with the non-functional new Pods.


## Usage

Add this registration statement to your codebase, so that it is picked up by the celery worker,
e.g. in the module where the celery application is defined.

```
import celery_worker_healthcheck

celery.signals.worker_init.connect(weak=False)(celery_worker_healthcheck.start)
```

Then configure the bind address for the healthcheck in your celery configuration:

```
worker_healthcheck_bind = '127.0.0.1:8001'
```

This starts an HTTP server in a thread;
on request it counts the number of workers that have notified they are ready
(using the [`worker_process_init` signal](https://docs.celeryq.dev/en/stable/userguide/signals.html#worker-process-init) to write a pid file).
If the required number of workers are ready, it returns HTTP 200, else 500.


## Configuration

These settings can be configured as part of the normal [celery configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html):

* `worker_healthcheck_bind` host:port on which to listen for healthcheck requests (default: None, i.e. healthcheck is disabled)
* `worker_healthcheck_minimum` count of workers that must be ready for the healthcheck to report success (default: 1)
* `worker_healthcheck_directory` directory in which to store the state files, one per worker (default: `''`, i.e. the current directory)
* `worker_healthcheck_filename` format string how to name the state files, must contain one placeholder `{}` for the pid (default: `'.celery.worker.{}'`)
