import hmac
import json
import time
import base64
import collections


# Written by @jmcarp originally
def order_recursive(data):
    """Recursively sort keys of input data and all its nested dictionaries.
    Used to ensure consistent ordering of JSON payloads.
    """
    if isinstance(data, dict):
        return collections.OrderedDict(
            sorted(
                (
                    (key, order_recursive(value))
                    for key, value in data.items()
                ),
                key=lambda item: item[0]
            )
        )
    if isinstance(data, list):
        return [
            order_recursive(value)
            for value in data
        ]
    return data


def serialize_payload(payload):
    ordered = order_recursive(payload)
    return base64.b64encode(json.dumps(ordered).encode('UTF-8'))


def unserialize_payload(message):
    payload = json.loads(base64.b64decode(message))
    return order_recursive(payload)


class Signer(object):

    def __init__(self, secret, digest):
        assert callable(digest)
        self.secret = secret
        self.digest = digest

    def sign_message(self, message):
        return hmac.new(
            key=self.secret,
            digestmod=self.digest,
            msg=message,
        ).hexdigest()

    def sign_payload(self, payload):
        message = serialize_payload(payload)
        signature = self.sign_message(message)
        return message, signature

    def verify_message(self, signature, message):
        expected = self.sign_message(message)
        return signature == expected

    def verify_payload(self, signature, payload):
        _, expected = self.sign_payload(payload)
        return signature == expected


def sign_data(signer, data, ttl=100):
    target = {'time': int(time.time() + ttl)}
    target.update(data)
    payload, signature = signer.sign_payload(target)
    return {
        'payload': payload.decode(),
        'signature': signature,
    }
