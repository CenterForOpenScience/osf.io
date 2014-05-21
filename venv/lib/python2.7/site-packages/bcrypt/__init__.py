"""OpenBSD Blowfish password hashing.

This module implements the OpenBSD Blowfish password hashing
algorithm, as described in "A Future-Adaptable Password Scheme" by
Niels Provos and David Mazieres.

This system hashes passwords using a version of Bruce Schneier's
Blowfish block cipher with modifications designed to raise the cost
of off-line password cracking. The computation cost of the algorithm
is parametised, so it can be increased as computers get faster.

Passwords are hashed using the hashpw() routine:

  hashpw(password, salt) -> hashed_password

Salts for the the second parameter may be randomly generated using the
gensalt() function:

  gensalt(log_rounds = 12) -> random_salt

The parameter "log_rounds" defines the complexity of the hashing. The
cost increases as 2**log_rounds.
"""

import os
from _bcrypt import *

def gensalt(log_rounds = 12):
	"""Generate a random text salt for use with hashpw(). "log_rounds"
	defines the complexity of the hashing, increasing the cost as
	2**log_rounds."""
	return encode_salt(os.urandom(16), min(max(log_rounds, 4), 31))

