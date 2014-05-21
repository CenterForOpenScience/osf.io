from wtforms.fields import Field
from wtforms.validators import Required

import widgets
import validators as local_validators


class RecaptchaField(Field):
    """Handles captcha field display and validation via reCaptcha"""

    widget = widgets.Recaptcha()

    def __init__(self, label='', validators=None, public_key=None, private_key=None, secure=False, http_proxy=None, **kwargs):
        # Pretty useless without the Recaptcha validator but still
        # user may want to subclass it, so keep it optional
        validators = validators or [local_validators.Recaptcha()]
        super(RecaptchaField, self).__init__(label, validators, **kwargs)

        if not public_key or not private_key:
            raise ValueError, 'Both recaptcha public and private keys are required.'

        self.public_key = public_key
        self.private_key = private_key
        self.secure = secure
        self.http_proxy = http_proxy

        self.ip_address = None
        self.challenge = None

    def process(self, formdata, data={}):
        """Handles multiple formdata fields that are required for reCaptcha.
        Only response field is handled as raw_data as it is the only user input
        """
        self.process_errors = []

        if isinstance(data, dict):
            self.ip_address = data.pop('ip_address', None)

        try:
            self.process_data(data)
        except ValueError, e:
            self.process_errors.append(e.args[0])

        if formdata is not None:
            # Developer must supply ip_address directly so throw a
            # non-validation exception if it's not present
            if not self.ip_address:
                raise ValueError, 'IP address is required.'

            try:
                # These fields are coming from the outside so keep them
                # inside the usual process
                challenge = formdata.getlist('recaptcha_challenge_field')
                if not challenge:
                    raise ValueError(self.gettext(u'Challenge data is required.'))
                self.challenge = challenge[0]

                # Pass user input as the raw_data
                self.raw_data = formdata.getlist('recaptcha_response_field')
                self.process_formdata(self.raw_data)
            except ValueError, e:
                self.process_errors.append(e.args[0])

        for filter in self.filters:
            try:
                self.data = filter(self.data)
            except ValueError, e:
                self.process_errors.append(e.args[0])

