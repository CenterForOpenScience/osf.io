class IdentifierAlreadyExists(Exception):
    pass

class ClientResponseError(Exception):

    def __init__(self, response):
        self.response = response
        super().__init__(f'Error response from client: {self.response.status_code}')
