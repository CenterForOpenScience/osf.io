<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    % if pending_moderation:
      The updates for ${resource_type} <a href="${parent_url}">"${title}"</a>
      were accepted and sent to ${provider} for moderation.
    % else:
      The updates for ${resource_type} <a href="${parent_url}">"${title}"</a>
      were accepted.
      <p>
      These updates will be visible by default along with the reason for the changes.
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
