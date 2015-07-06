import requests

class FileHandler:

    def __init__(self, pid):
        self.pid = pid


    def get_file_list(self):
        uri = "http://localhost:8000"
        path = "/v2/nodes/" + self.pid + "/files/?provider=osfstorage&format=json"
        return requests.get(uri+path).json()


    def read_file(self, file):
        #url = self.get_file_url(file.get('name'))
        url = file['links'].get('self')
        response = requests.get(url)
        return response._content


    def get_posts(self, file):
        blog = self.get_file_list()['data']
        index = blog.index(filter(lambda post: post['name'] == file, blog)[0])
        curr = blog[index]
        try:
            assert (index-1) >= 0
            prev = blog[index-1]
        except (IndexError, AssertionError):
            prev = None
        try:
            next = blog[index+1]
        except IndexError:
            next = None
        return prev, curr, next
