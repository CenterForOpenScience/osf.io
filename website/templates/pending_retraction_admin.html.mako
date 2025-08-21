<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    % if is_initiator:
      You have requested final approvals to withdraw your registration
      titled <a href="${registration_link}">${reviewable_title}</a>
    % else:
      ${initiated_by} has requested final approvals to withdraw your registration
      titled <a href="${registration_link}">${reviewable_title}</a>
    % endif
    </p>
    % if reviewable.withdrawal_justification:
      <p>
      The registration is being withdrawn for the following reason:
      <blockquote>${reviewable.withdrawal_justification}</blockquote>
      </p>
    % endif
    <p>
    % if is_moderated:
      If approved by all admin contributors, the withdrawal request will be submitted for moderator review.
      If the moderators approve, the registration will be marked as withdrawn.
    % else:
      If approved by all admin contributors, the registration will be marked as withdrawn.
    % endif
    Its content will be removed from the
    <a href="${domain}/registries/${reviewable_provider__id if reviewable_provider__id else 'osf'}">${reviewable_provider_name if reviewable_provider__id else "OSF Registry"}</a>,
    but basic metadata will be left behind. The title of the withdrawn registration and its list of contributors will remain.
    % if reviewable.withdrawal_justification:
      The provided justification or explanation of the withdrawal will also be visible.
    % endif
    </p>
    % if not reviewable.branched_from_node:
      <p>
      Even if the registration is withdrawn, the <a href="${reviewable.registered_from.absolute_url}">OSF Project</a>
      created for this registration will remain available.
      </p>
    % endif
    <p style="color:red;">
    You have ${approval_time_span} hours from midnight tonight (EDT) to approve or cancel this
    withdrawal request before it is automatically submitted.
    </p>
    <p>
    To approve this withdrawal: <a href="${approval_link}">Click here</a>.<br>
    To cancel this withdrawal: <a href="${disapproval_link}">Click here</a>.
    </p>
    <p>
    Note: If any admin clicks their cancel link, the pending withdrawal will be
    cancelled immediately and the registration will remain public. This operation is irreversible.
    </p>
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
