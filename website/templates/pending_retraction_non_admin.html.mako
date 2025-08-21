<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user_fullname},
    <p>
    ${initiated_by} has requested final approval to withdraw your registration
    titled <a href="${registration_link}">${reviewable_title}</a>
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
    <p>
    Admins have ${approval_time_span} hours from midnight tonight (EDT) to approve or cancel
    the withdrawal request before the withdrawal is automatically submitted.
    </p>
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
    </p>
</tr>
</%def>
