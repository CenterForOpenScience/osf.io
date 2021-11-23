<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    % if needs_moderation:
      The updates for ${resource_type} <a href="${parent_url}">"${title}"</a>
      were accepted.
      <p>
      These updates will be visibly be default along with the reason for the changes.
    % else:
      The updates for ${resource_type} <a href="${parent_url}">"${title}"</a>
      were accepted and sent to ${provider} for moderation.
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
