import secrets
from base64 import b32encode
from datetime import datetime, timedelta
from typing import Final

from addons.base.models import BaseUserSettings
from django.db import models
from pyotp import TOTP


TOKEN_LENGTH: Final[int] = 30
DRIFT_PERIOD: Final[int] = 30


class UserSettings(BaseUserSettings):
    totp_secret = models.TextField(null=True, blank=True)  # hexadecimal
    totp_drift = models.IntegerField(default=1)
    is_confirmed = models.BooleanField(default=False)

    @property
    def totp_secret_b32(self) -> str:
        return b32encode(self.totp_secret.encode()).decode()

    @property
    def otpauth_url(self) -> str:
        return f'otpauth://totp/OSF:{self.owner.username}?secret={self.totp_secret_b32}'

    def to_json(self, user):
        rv = super().to_json(user)
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

    def verify_code(self, code: int | str) -> bool:
        client = TOTP(self.totp_secret_b32)
        accepted = client.verify(
            otp=str(code),
            for_time=datetime.now() + timedelta(seconds=self.totp_drift * DRIFT_PERIOD),
            valid_window=1
        )
        if accepted:
            self.totp_drift += 1
            return True
        self.totp_drift = 0
        return False

    #############
    # Callbacks #
    #############

    def on_add(self) -> None:
        super().on_add()
        self.totp_secret = secrets.token_urlsafe(TOKEN_LENGTH)
        self.totp_drift = 0
        self.is_confirmed = False

    def on_delete(self) -> None:
        super().on_delete()
        self.totp_secret = None
        self.totp_drift = 0
        self.is_confirmed = False
