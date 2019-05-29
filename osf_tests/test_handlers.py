import pytest
from nose.tools import assert_raises

from framework.celery_tasks import handlers
from website.project.tasks import on_node_updated


class TestCeleryHandlers:

    @pytest.fixture()
    def queue(self):
        return handlers.queue()

    def test_get_task_from_queue_not_there(self):
        task = handlers.get_task_from_queue(
            'website.project.tasks.on_node_updated',
            predicate=lambda task: task.kwargs['node_id'] == 'woop'
        )
        assert task is False

    def test_get_task_from_queue(self, queue):
        handlers.queue().append(
            on_node_updated.s(node_id='woop', user_id='heyyo', first_save=False, saved_fields={'contributors'})
        )
        task = handlers.get_task_from_queue(
            'website.project.tasks.on_node_updated',
            predicate=lambda task: task.kwargs['node_id'] == 'woop'
        )
        assert task

    def test_get_task_from_queue_errors_with_two_tasks(self, queue):
        tasks = [
            on_node_updated.s(node_id='woop', user_id='heyyo', first_save=False, saved_fields={'title'}),
            on_node_updated.s(node_id='woop', user_id='heyyo', first_save=False, saved_fields={'contributors'})
        ]
        queue += tasks

        with assert_raises(ValueError):
            handlers.get_task_from_queue(
                'website.project.tasks.on_node_updated',
                predicate=lambda task: task.kwargs['node_id'] == 'woop'
            )
