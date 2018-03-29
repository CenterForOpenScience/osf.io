<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    You have been added by ${referrer.fullname} as ${role} to ${provider.name}, powered by OSF.<br>
    <br>
    You will automatically be subscribed to notification emails for new ${provider.preprint_word} submissions to ${provider.name}. To change your email notification preferences, visit your notification settings: ${notification_url}<br>
    <br>
    If you are not ${user.fullname} or you have been erroneously associated with ${provider.name}, email contact+${provider._id}@osf.io with the subject line "Claiming Error" to report the problem.<br>
    <br>
    Sincerely,<br>
    <br>
    Your ${provider.name} and OSF teams<br>
</tr>
</%def>
