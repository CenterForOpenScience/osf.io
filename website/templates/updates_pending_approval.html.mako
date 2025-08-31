<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    % if is_initiator:
      You submitted updates for ${resource_type} <a href="${parent_url}">"${title}"</a>
      for Admin approval.
    % else:
      ${initiator_fullname} submitted updates for ${resource_type} <a href="${parent_url}">"${title}"</a>
      for Admin approval.
    % endif
    <p>
    % if is_approver:
      <a href="${update_url}">Click here</a> to review and either approve or reject the
      submitted updates. Decisions must be made within
      ${registration_approval_time} hours.
    % else:
      <a href="${update_url}">Click here</a> to review the submited updates.
      Admins have up to ${int(settings.REGISTRATION_UPDATE_APPROVAL_TIME.total_seconds() / 3600)} hours
      to make their decision.
    % endif
    <p>
    Accepted updates will be displayed on the ${resource_type} along with why they were needed.
    <p>
    Updates that need additional edits will be returned to draft form.
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
