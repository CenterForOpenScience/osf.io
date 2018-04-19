<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${admin.fullname},<br>
    <br>
    <a href="${requester.absolute_url}">${requester.fullname}</a> has requested access to your ${node.project_or_component} "<a href="${node.absolute_url}">${node.title}</a>".<br>
    <br>
    To review the request, click <a href="${contributors_url}">here</a> to allow or deny access and configure permissions.<br>
    <br>
    This request is being sent to you because your project has the 'Request Access' feature enabled. This allows potential collaborators to request to be added to your project. To disable this feature, click <a href="${project_settings_url}">here</a>.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>
    <br>
    Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email contact@osf.io<br>
</tr>
</%def>
