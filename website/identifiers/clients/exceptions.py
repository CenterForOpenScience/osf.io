class IdentifierAlreadyExists(Exception):
    pass

class ClientResponseError(Exception):

    def __init__(self, response):
        self.response = response
        super(ClientResponseError, self).__init__('Error response from client: {}'.format(self.response.status_code))
