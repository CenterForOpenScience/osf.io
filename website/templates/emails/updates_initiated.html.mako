<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    % if is_initiator:
      You initiated updates for ${resource_type} <a href="${parent_url}">"${title}"</a>.
    % else:
      ${initiator} initiated updates for ${resource_type} <a href="${parent_url}">"${title}"</a>.
    % endif
    <p>
    % if can_write:
      <a href="${update_url}">Click here</a> to review and contribute to the updates in progress.
    % else:
      <a href="${update_url}">Click here</a> to review the updates in progress.
    % endif
    <p>
    Sincerely,<br>
    The OSF Team
    <p>
    <p>
    Want more information? Visit <a href="${settings.DOMAIN}">${settings.DOMAIN}</a> to learn about the OSF,
    or <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization,
    the Center for Open Science.
    <p>
    Questions? Email <a href="mailto:${settings.OSF_CONTACT_EMAIL}">${settings.OSF_CONTACT_EMAIL}</a>
</tr>
</%def>
