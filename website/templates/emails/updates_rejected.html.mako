<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    % if is_initiator:
      You did not accept the updates for ${resource_type} <a href="${parent_url}">"${title}"</a>.
    % else:
      ${initiator} did not accept the updates for ${resource_type} <a href="${parent_url}">"${title}"</a>.
    % endif
    <p>
    % if can_write:
      The updates for the ${resource_type} were returned back to a draft so additional edits can be made.
    % else:
      The updates for the ${resource_type} were returned back to a draft so Admin and Write contributors
      can make additional edits.
    % endif
    <p>
    Sincerely,<br>
    The OSF Team
    <p>
    <p>
    Want more information? Visit <a href="${domain}">${domain}</a> to learn about the OSF,
    or <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization,
    the Center for Open Science.
    <p>
    Questions? Email <a href="mailto:${osf_contact_email}}">${osf_contact_email}}</a>
  </td>
</tr>
</%def>
