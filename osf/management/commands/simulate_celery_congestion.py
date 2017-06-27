# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from random import randint
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from framework.celery_tasks import app
from website.settings import DEFAULT_QUEUE, LOW_QUEUE, MED_QUEUE, HIGH_QUEUE

LOW_SLEEP_TIME = 10.0
DEF_SLEEP_TIME = 3.0
MED_SLEEP_TIME = 1.0
HIGH_SLEEP_TIME = 0.1

CONGESTION_THRESHOLD = 30.0

QUEUES = [DEFAULT_QUEUE, LOW_QUEUE, MED_QUEUE, HIGH_QUEUE]

class CeleryRouter(object):
    def route_for_task(self, task, args=None, kwargs=None):
        # LOW_QUEUE = low
        # DEFAULT_QUEUE = celery
        # MED_QUEUE = med
        # HIGH_QUEUE = high
        queue = task.split('.')[-1].split('_')[0]
        if queue not in QUEUES:
            queue = DEFAULT_QUEUE
        return {
            'queue': queue
        }

app.conf['CELERY_ROUTES'] = ('{}.CeleryRouter'.format(__name__))

def detect_congestion(queue_time):
    if (timezone.now() - queue_time).total_seconds() > CONGESTION_THRESHOLD:
        print('CONGESTION DETECTED')

@app.task
def low_task(queue_time):
    print('Low task scheduled at {} now running'.format(queue_time.isoformat()))
    # Don't care about congestion for LOW
    time.sleep(LOW_SLEEP_TIME)

@app.task
def def_task(queue_time):
    print('Default task scheduled at {} now running'.format(queue_time.isoformat()))
    detect_congestion(queue_time)
    time.sleep(DEF_SLEEP_TIME)

@app.task
def med_task(queue_time):
    print('Medium task scheduled at {} now running'.format(queue_time.isoformat()))
    detect_congestion(queue_time)
    time.sleep(MED_SLEEP_TIME)

@app.task
def high_task(queue_time):
    print('High task scheduled at {} now running'.format(queue_time.isoformat()))
    detect_congestion(queue_time)
    time.sleep(HIGH_SLEEP_TIME)


class Command(BaseCommand):
    """
    Strip trailing whitespace from osf_subject.text
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--workers',
            dest='workers',
            type=int,
            default=1,
            help='Number of workers to initialize',
        )
        parser.add_argument(
            '--wargs',
            dest='worker_args',
            type=str,
            nargs='*',
            default=['--purge -Ofair -l DEBUG'],
            help="""
            List of celery argments to send to each worker.
            Length either be 1 (same per worker) or match `--workers` (specified per worker).
            Run `celery worker --help` for options.
            Example: --wargs '-Ofair -l DEBUG -c 2 -X low' '-Ofair -l DEBUG -c 2'
            """
        )
        parser.add_argument(
            '--lj',
            dest='low_jobs',
            type=int,
            default=10,
            help='Number of LOW_QUEUE jobs to queue',
        )
        parser.add_argument(
            '--dj',
            dest='def_jobs',
            type=int,
            default=10,
            help='Number of DEFAULT_QUEUE jobs to queue',
        )
        parser.add_argument(
            '--mj',
            dest='med_jobs',
            type=int,
            default=20,
            help='Number of MED_QUEUE jobs to queue',
        )
        parser.add_argument(
            '--hj',
            dest='high_jobs',
            type=int,
            default=50,
            help='Number of HIGH_QUEUE jobs to queue',
        )
        parser.add_argument(
            '--ls',
            dest='low_sleep',
            type=float,
            default=10.0,
            help='Sleep duration for low jobs',
        )
        parser.add_argument(
            '--ds',
            dest='def_sleep',
            type=float,
            default=3.0,
            help='Sleep duration for default jobs',
        )
        parser.add_argument(
            '--ms',
            dest='med_sleep',
            type=float,
            default=1.0,
            help='Sleep duration for medium jobs',
        )
        parser.add_argument(
            '--hs',
            dest='high_sleep',
            type=float,
            default=0.2,
            help='Sleep duration for high jobs',
        )
        parser.add_argument(
            '--ct',
            dest='congestion_threshold',
            type=float,
            default=30.0,
            help='Congestion threshold.'
        )
        parser.add_argument(
            '--wt',
            dest='wait_time',
            type=int,
            default=45,
            help='Time to wait for user to start celery.'
        )

    def handle(self, *args, **options):
        global LOW_SLEEP_TIME
        global DEF_SLEEP_TIME
        global MED_SLEEP_TIME
        global HIGH_SLEEP_TIME
        global CONGESTION_THRESHOLD
        LOW_SLEEP_TIME = options['low_sleep']
        DEF_SLEEP_TIME = options['def_sleep']
        MED_SLEEP_TIME = options['med_sleep']
        HIGH_SLEEP_TIME = options['high_sleep']
        CONGESTION_THRESHOLD = options['congestion_threshold']

        if len(options['worker_args']) != 1 and len(options['worker_args']) != options['workers']:
            raise Exception('Issue with worker_args count')

        print('Run the following command(s) in another terminal. Waiting {} seconds for you to do so:\n'.format(options['wait_time']))
        for i in range(options['workers']):
            wargs = options['worker_args'][i] if len(options['worker_args']) > 1 else options['worker_args'][0]
            cmd = 'export DJANGO_SETTINGS_MODULE=api.base.settings && celery worker -A {}.app {}'.format(__name__, wargs)
            print(cmd)

        jobs = []
        for _ in range(options['high_jobs']):
            jobs.append(high_task)
        for _ in range(options['med_jobs']):
            jobs.append(med_task)
        for _ in range(options['def_jobs']):
            jobs.append(def_task)
        for _ in range(options['low_jobs']):
            jobs.append(low_task)

        time.sleep(options['wait_time'])
        while jobs:
            i = randint(0, len(jobs)-1)
            jobs[i].delay(timezone.now())
            jobs.pop(i)
