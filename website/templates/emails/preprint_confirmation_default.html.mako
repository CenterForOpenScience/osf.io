<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>
    Congratulations on sharing your preprint "${preprint.title}" on OSF Preprints: ${preprint.absolute_url}<br>
    <br>
    Now that you've shared your preprint, take advantage of more OSF features:<br>
    <br>
    % if node:
        *Upload supplemental, materials, data, and code to the OSF project associated with your preprint: ${node.absolute_url} Learn how: http://help.osf.io/m/preprints/l/685323-add-supplemental-files-to-a-preprint<br>
        <br>
    % endif
    *Preregister your next study and become eligible for a $1000 prize: osf.io/prereg<br>
    <br>
    *Track your impact with preprint downloads<br>
    <br>
    <br>
    You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '} notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + 'settings/notifications/'}<br>
    <br>
    Sincerely,<br>
    <br>
    Your OSF Team<br>
    <br>
    Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>

</tr>
</%def>
