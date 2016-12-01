from base64 import b32encode
from binascii import unhexlify
from random import SystemRandom

from addons.base.models import BaseUserSettings
from django.db import models
from oath import accept_totp


class UserSettings(BaseUserSettings):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.addons.twofactor.models.TwoFactorUserSettings'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    totp_secret = models.TextField(null=True, blank=True)  # hexadecimal
    totp_drift = models.IntegerField()
    is_confirmed = models.BooleanField(default=False)

    @property
    def totp_secret_b32(self):
        return b32encode(unhexlify(self.totp_secret))

    @property
    def otpauth_url(self):
        return 'otpauth://totp/OSF:{}?secret={}'.format(self.owner.username,
                                                        self.totp_secret_b32)

    def to_json(self, user):
        rv = super(UserSettings, self).to_json(user)
        rv.update({
            'is_enabled': True,
            'is_confirmed': self.is_confirmed,
            'secret': self.totp_secret_b32,
            'drift': self.totp_drift,
        })
        return rv

    ###################
    # Utility methods #
    ###################

    def verify_code(self, code):
        accepted, drift = accept_totp(key=self.totp_secret,
                                      response=code,
                                      drift=self.totp_drift)
        if accepted:
            self.totp_drift = drift
            return True
        return False

    #############
    # Callbacks #
    #############

    def on_add(self):
        super(UserSettings, self).on_add()
        self.totp_secret = _generate_seed()
        self.totp_drift = 0
        self.is_confirmed = False

    def on_delete(self):
        super(UserSettings, self).on_delete()
        self.totp_secret = None
        self.totp_drift = 0
        self.is_confirmed = False


def _generate_seed():
    """Generate a new random seed

    The length of the returned string will be a multiple of two, and
    stripped of type specifier "0x" that `hex()` prepends.

    :return str: A random, padded hex value
    """
    x = SystemRandom().randint(0, 32 ** 16 - 1)
    h = hex(x).strip('L')[2:]
    if len(h) % 2:
        h = '0' + h
    return h
