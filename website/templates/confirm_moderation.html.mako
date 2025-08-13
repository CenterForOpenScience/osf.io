<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},<br>
    <br>
    You have been added by ${referrer_fullname}, as ${'an administrator' if is_admin else 'a moderator'} to ${provider_name}, powered by OSF. To set a password for your account, visit:<br>
    <br>
    ${claim_url}<br>
    <br>
    Once you have set a password you will be able to moderate, create and approve your own submissions. You will automatically be subscribed to notification emails for new submissions to ${provider_name}.<br>
    <br>
    If you are not ${user_fullname} or you have been erroneously associated with ${provider_name}, email contact+${provider__id}@osf.io with the subject line "Claiming error" to report the problem.<br>
    <br>
    Sincerely,<br>
    Your ${provider_name} and OSF teams<br>
</tr>
</%def>
