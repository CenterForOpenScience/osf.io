import ast
from pathlib import Path


def _storage_usage_task():
    module = ast.parse(Path(__file__).with_name('tasks.py').read_text())
    return module, next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == 'update_storage_usage_cache'
    )


def test_update_storage_usage_cache_has_time_limits():
    _, task = _storage_usage_task()
    decorator = next(
        node
        for node in task.decorator_list
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'task'
    )
    options = {keyword.arg: ast.literal_eval(keyword.value) for keyword in decorator.keywords}

    assert options['soft_time_limit'] == 270
    assert options['time_limit'] == 300


def test_update_storage_usage_cache_logs_guid_and_reraises_soft_timeout():
    module, task = _storage_usage_task()
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == 'billiard.exceptions'
        and any(alias.name == 'SoftTimeLimitExceeded' for alias in node.names)
        for node in module.body
    )
    handler = next(
        node
        for node in ast.walk(task)
        if isinstance(node, ast.ExceptHandler)
        and isinstance(node.type, ast.Name)
        and node.type.id == 'SoftTimeLimitExceeded'
    )
    log_call = next(
        node
        for node in ast.walk(handler)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'exception'
    )

    assert any(isinstance(arg, ast.Name) and arg.id == 'target_guid' for arg in log_call.args)
    assert any(isinstance(node, ast.Raise) for node in handler.body)
