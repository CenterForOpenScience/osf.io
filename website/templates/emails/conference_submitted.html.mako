<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${fullname},<br>
    <br>
    Congratulations! You have successfully added your ${conf_full_name} ${presentation_type} to OSF.<br>
    <br>
    % if user_created:
    Your account on OSF has been created. To claim your account, please create a password by clicking here: ${set_password_url}. Please verify your profile information at: ${profile_url}.<br>
    <br>
    % endif
    You now have a permanent, citable URL, that you can share: ${node_url}. All submissions for ${conf_full_name} may be viewed at the following link: ${conf_view_url}.<br>
    <br>
    % if is_spam:
    Your email was flagged as spam by our mail processing service. To prevent potential spam, we have made your project private. If this is a real project, please log in to your account, browse to your project, and click the "Make Public" button so that other users can view it.<br>
    <br>
    % endif
    Get more from OSF by enhancing your project with the following:<br>
    <br>
    * Collaborators/contributors to the submission<br>
    * Charts, graphs, and data that didn't make it onto the submission<br>
    * Links to related publications or reference lists<br>
    * Connecting other accounts, like Dropbox, Google Drive, GitHub, figshare and Mendeley via add-on integration. Learn more and read the full list of available add-ons <a href="https://openscience.zendesk.com/hc/en-us/categories/360001550973/?utm_source=notification&utm_medium=email&utm_campaign=conference_submitted">here.</a><br>
    <br>
    To learn more about OSF, read the <a href="https://openscience.zendesk.com/hc/en-us/?utm_source=notification&utm_medium=email&utm_campaign=conference_submitted">Guides</a>.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>

</tr>
</%def>
