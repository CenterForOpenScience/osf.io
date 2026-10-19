from dj_celery_panel.celery_utils import CeleryQueuesInspectBackend, QueueDetailPage, QueueListPage


class RoutedTasksQueuesBackend(CeleryQueuesInspectBackend):
    """dj-celery-panel queues backend that also lists the tasks routed to each queue
    and the configured queues that no active worker consumes.

    Routes are resolved the same way Celery does when sending a task, so explicit
    queue= overrides passed to apply_async() at call time are not reflected.
    """

    BACKEND_DESCRIPTION = 'Queue bindings, routing configuration, routed tasks and unconsumed queues'

    def get_queues(self):
        page = super().get_queues()
        # Workers report only the queues they consume, so a configured queue nobody consumes
        # would be missing from the list while tasks routed to it pile up
        listed = {queue['name'] for queue in page.queues}
        unconsumed = [
            self.describe_unconsumed_queue(queue)
            for name, queue in sorted(self.app.amqp.queues.items())
            if name not in listed
        ]
        return QueueListPage(queues=page.queues + unconsumed, error=page.error)

    def get_queue_detail(self, queue_name):
        page = super().get_queue_detail(queue_name)
        queue, error = page.queue, page.error
        if queue is None:
            # membership check first: indexing Queues creates missing ones
            if queue_name not in self.app.amqp.queues:
                return page
            queue = self.describe_unconsumed_queue(self.app.amqp.queues[queue_name])
            error = 'No active worker consumes this queue'
        routed_tasks = self.get_routed_tasks(queue_name, self.get_task_names(queue['workers']))
        return QueueDetailPage(
            queue={**queue, 'routed_tasks': routed_tasks},
            error=error,
        )

    def describe_unconsumed_queue(self, queue):
        broker_info = self._get_queue_length_from_broker(queue.name)
        return {
            'name': queue.name,
            'exchange': queue.exchange.name,
            'exchange_type': queue.exchange.type,
            'routing_key': queue.routing_key,
            'durable': queue.durable,
            'auto_delete': queue.auto_delete,
            'exclusive': queue.exclusive,
            'arguments': queue.queue_arguments,
            'workers': [],
            'worker_details': [],
            'message_count': broker_info.get('length'),
            'consumer_count': broker_info.get('consumer_count'),
            'broker_query_error': broker_info.get('error'),
        }

    def get_task_names(self, workers):
        # The admin process registers only the task modules it happens to import,
        # so ask the workers for the tasks they have registered: the ones consuming
        # this queue, or all of them when nobody consumes it
        registered = self.app.control.inspect(destination=workers or None).registered() or {}
        names = {name for worker_tasks in registered.values() for name in worker_tasks}
        return {name for name in names | set(self.app.tasks) if not name.startswith('celery.')}

    def get_routed_tasks(self, queue_name, task_names):
        router = self.app.amqp.router
        routed_tasks = []
        for name in task_names:
            task = self.app.tasks.get(name)
            options = dict(task._get_exec_options()) if task else {}
            if router.route(options, name)['queue'].name == queue_name:
                routed_tasks.append(name)
        return sorted(routed_tasks)
