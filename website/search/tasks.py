from framework.tasks import app
from website.search import search


@app.task
def update_file_task(file_node, index=None):
    search.update_file(file_node, index)


@app.task
def delete_file_task(file_node, index=None):
    search.delete_file(file_node, index)


@app.task
def update_all_files_task(node, index=None):
    search.update_all_files(node, index)


@app.task
def delete_all_files_task(node, index=None):
    search.delete_all_files(node, index)
