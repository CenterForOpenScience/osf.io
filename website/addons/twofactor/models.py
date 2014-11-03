from base64 import b32encode
from binascii import unhexlify
from random import SystemRandom

from modularodm.fields import BooleanField, StringField, IntegerField
from oath import accept_totp

from framework.status import push_status_message
from website.addons.base import AddonUserSettingsBase


class TwoFactorUserSettings(AddonUserSettingsBase):
    totp_secret = StringField()  # hexadecimal
    totp_drift = IntegerField()
    is_confirmed = BooleanField(default=False)

    @property
    def totp_secret_b32(self):
        return b32encode(unhexlify(self.totp_secret))

    @property
    def otpauth_url(self):
        return 'otpauth://totp/OSF:{}?secret={}'.format(self.owner.username,
                                                        self.totp_secret_b32)

    def to_json(self, user):
        rv = super(TwoFactorUserSettings, self).to_json(user)
        rv.update({
            'is_confirmed': self.is_confirmed,
            'secret': self.totp_secret_b32,
            'drift': self.totp_drift,
            'otpauth_url': self.otpauth_url,
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
        push_status_message(
            message='Please <a href="#TfaVerify">activate your device</a> '
                    'before continuing.',
            safe=True,
        )
        super(TwoFactorUserSettings, self).on_add()
        self.totp_secret = _generate_seed()
        self.totp_drift = 0
        self.is_confirmed = False

    def on_delete(self):
        if self.is_confirmed:
            push_status_message('Successfully deauthorized two-factor'
                                ' authentication. Please delete the'
                                ' verification code on your device.')
        super(TwoFactorUserSettings, self).on_delete()
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
