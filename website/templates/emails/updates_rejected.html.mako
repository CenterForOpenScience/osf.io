<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    % if is_initiator:
      You did not accept the updates for ${resource_type} <a href="${parent_url}">"${title}".
    % else:
      ${initiator}  did not accept the updates for ${resource_type} <a href="${parent_url}">"${title}".
    % endif
    <p>
    % if can_write:
      The ${resource_type} was returned back to a draft so additinoal updates can be made.
    % else:
      The ${resource_type} was returned back to a draft so Admin and Write contributors
      can make additinoal updates.
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
  </td>
</tr>
</%def>
