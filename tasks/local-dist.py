from invoke import task


@task()
def example_task(ctx, echo_this):
    """
    An example task which prints using bash.
    :param ctx:
    :param echo_this str:
    :return:
    """
    ctx.run('echo {}'.format(echo_this))
