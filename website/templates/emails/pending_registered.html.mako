<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${fullname},<br>
    <br>
    We received your request to become a contributor for "${node.title}". <br>
    <br>
    To confirm your identity, ${referrer.fullname} has been sent an email to forward to you with your confirmation link.<br>
    <br>
    This link will allow you to contribute to "${node.title}".<br>
    <br>
    Thank you for your patience.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>

</tr>
</%def>
