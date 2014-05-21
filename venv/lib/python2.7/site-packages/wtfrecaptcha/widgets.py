# Template for the widget
RECAPTCHA_HTML = u"""<script type="text/javascript"
 src="%(protocol)s://www.google.com/recaptcha/api/challenge?k=%(public_key)s">
</script>
<noscript>
 <iframe src="%(protocol)s://www.google.com/recaptcha/api/noscript?k=%(public_key)s"
     height="300" width="500" frameborder="0"></iframe><br>
 <textarea name="recaptcha_challenge_field" rows="3" cols="40">
 </textarea>
 <input type="hidden" name="recaptcha_response_field"
     value="manual_challenge">
</noscript>"""

class Recaptcha(object):
    """Recaptcha widget that displays HTML depending on security status"""

    def __call__(self, field, **kwargs):
        html = RECAPTCHA_HTML % {
                'protocol': field.secure and 'https' or 'http',
                'public_key': field.public_key
        }
        return html
