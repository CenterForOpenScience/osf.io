<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${admin.fullname},<br>
    <br>
    ${requester.fullname} (${requester.absolute_url}) has requested access to your ${node.project_or_component} "${node.title}" (${node.absolute_url}).<br>
    <br>
    To review the request, click here ${contributors_url} to allow or deny access and configure permissions.<br>
    <br>
    This request is being sent to you because your project has the 'Request Access' feature enabled. This allows potential collaborators to request to be added to your project. To disable this feature, click here ${project_settings_url}<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>
    <br>
    Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>


</tr>
</%def>
