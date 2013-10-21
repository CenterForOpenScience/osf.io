import simpleflake

EPOCH = 1288834974657L / 1000.
ALPHABET = '23456789abcdefghijkmnpqrstuvwxyz'


def base_encode(num, alphabet=ALPHABET):
    """Encode a number in given base

    :param num: The number to encode
    :param alphabet: The alphabet to use for encoding

    """
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
        arr.reverse()
    return ''.join(arr)


def make_encoded_snowflake():
    return base_encode(simpleflake.simpleflake(epoch=EPOCH))
