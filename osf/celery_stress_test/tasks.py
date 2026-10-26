import time

from celery import shared_task, current_app


@shared_task(name='stress_testing.start_celery_stress_test')
def start_celery_stress_test(config):
    duration = config['total_duration']
    max_rate = config['max_total_rate']
    workloads = config['workloads']

    if not workloads:
        return

    started_at = time.monotonic()
    next_run = [started_at] * len(workloads)
    global_interval = 1 / max_rate
    next_global_run = started_at
    start_index = 0

    while time.monotonic() - started_at < duration:
        now = time.monotonic()

        if now < next_global_run:
            time.sleep(min(next_global_run - now, 0.01))
            continue

        published = False

        # Rotate which workload gets first access to the next global slot.
        for offset in range(len(workloads)):
            index = (start_index + offset) % len(workloads)
            workload = workloads[index]

            if now < next_run[index]:
                continue

            current_app.send_task(
                'stress_testing.simulated_workload',
                kwargs={
                    'mode': workload['mode'],
                    'io_seconds': workload.get('io_seconds', 1),
                    'cpu_iterations': workload.get(
                        'cpu_iterations',
                        1_000_000,
                    ),
                },
                queue=workload['queue'],
            )

            next_run[index] = now + 1 / workload['rate']
            next_global_run = now + global_interval
            start_index = (index + 1) % len(workloads)
            published = True
            break

        if not published:
            next_due = min(next_run)
            sleep_for = max(0.001, min(next_due - now, 0.01))
            time.sleep(sleep_for)


@shared_task(name='stress_testing.simulated_workload')
def simulated_workload(
    mode='io',
    io_seconds=1.0,
    cpu_iterations=1_000_000,
):
    """
    Simulate an I/O-bound, CPU-bound, or mixed workload.

    Args:
        mode: "io", "cpu", or "mixed".
        io_seconds: Duration of simulated I/O in seconds.
        cpu_iterations: Number of iterations for CPU-bound work.
    """
    if mode not in {'io', 'cpu', 'mixed'}:
        raise ValueError(f"Unsupported workload mode: {mode}")

    if not 0 <= io_seconds <= 30:
        raise ValueError('io_seconds must be between 0 and 30')

    if not 1 <= cpu_iterations <= 100_000_000:
        raise ValueError('cpu_iterations must be between 1 and 100,000,000')

    if mode in {'io', 'mixed'}:
        time.sleep(io_seconds)

    if mode in {'cpu', 'mixed'}:
        result = 0
        for i in range(cpu_iterations):
            result += i * i

    return None
