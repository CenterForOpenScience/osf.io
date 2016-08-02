import webbrowser

from invoke import task, run

# TODO: test task

@task
def flake(ctx):
    """Run flake8 on codebase."""
    run('flake8 .', echo=True)

@task
def readme(ctx, browse=False):
    run("rst2html.py README.rst > README.html")
    if browse:
        webbrowser.open_new_tab('README.html')
