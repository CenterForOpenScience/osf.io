<%inherit file="website/templates/notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},<br>
    <br>
    We received your request to become a contributor for "${node_title}". <br>
    <br>
    To confirm your identity, ${referrer_fullname} has been sent an email to forward to you with your confirmation link.<br>
    <br>
    This link will allow you to contribute to "${node_title}".<br>
    <br>
    Thank you for your patience.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>

</tr>
</%def>
