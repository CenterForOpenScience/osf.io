<%inherit file="notify_base.mako" />

<%def name="content()">
<% from website import settings %>
<tr>
  <td style="border-collapse: collapse; line-height: 1.5;">
    Hello ${user.fullname},<br>
    <br>
    This email is about your account on OSF. You have connected Mendeley to one or more of your projects.
    <br>
    <br>
    Recently, Mendeley updated their terms of use to comply with new European data privacy laws. This will require you to reauthorize the connection your account has to this add-on. You 
    can do this quickly by navigating to your account settings page, 
    then click "Configure add-on accounts". Get there directly using <a href="${settings.DOMAIN}settings/addons/">this link</a>. 
    From there, click <strong>Connect or Reauthorize Account</strong>. You will be redirected 
    to the Mendeley site to authorize the connection.
    <br>
    <br>
    Until you reauthorize the connection between your account and Mendeley, your Mendeley library will not display correctly on the OSF.
    <br>
    <br>
    We apologize for any inconvenience. Please don't hesitate to email <a href="mailto:support@osf.io">support@osf.io</a> with questions.
    <br>
    <br>
    Sincerely,
    <br>
    The OSF Team
  </td>
</tr>
</%def>
