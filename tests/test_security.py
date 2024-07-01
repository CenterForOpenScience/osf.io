from framework.encryption import encrypt, decrypt
from website import security


def test_random_string():
    s = security.random_string(length=30)
    assert isinstance(s, str)
    assert len(s) == 30
    s2 = security.random_string(30)
    assert s != s2


def test_encryption():
    private_string = b'p4ssw0rd'

    # Encrypted string is obfuscated
    encrypted_string = encrypt(private_string)
    assert private_string not in encrypted_string

    # Original string can be recovered
    decrypted_string = decrypt(encrypted_string)
    assert decrypted_string == private_string
