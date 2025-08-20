<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    ${initiated_by} has requested final approvals to submit your registration
	titled <a href="${registration_link}">${reviewable_title}</a>
    </p>
    <p>
    % if is_moderated:
      If approved by all admin contributors, the registration will be submitted for moderator review.
      If the moderators approve, the registration will be embargoed until
      ${embargo_end_date}, at which time it will be made public as part of the
      <a href="${domain}/registries/${reviewable_provider__id if reviewable_provider else 'osf'}">${reviewable_provider_name if reviewable_provider else "OSF Registry"}</a>.
    % else:
      If approved by all admin contributors, the registration will be embargoed until
      ${embargo_end_date}, at which point it will be made public as part of the
      <a href="${domain}/registries/${reviewable_provider__id if reviewable_provider else 'osf'}">${reviewable_provider_name if reviewable_provider else "OSF Registry"}</a>.
    % endif
    </p>
    <p>
    Admins have ${approval_time_span} hours from midnight tonight (EDT) to approve or cancel the
    registration before the registration is automatically submitted.
    </p>
    % if not reviewable.branched_from_node:
      <p>
      An <a href="${reviewable_registered_from_absolute_url}">OSF Project</a> was created from
	  this registration to support continued collaboration and sharing of your research.
      This project will remain available even if your registration is rejected.
      </p>
      <p>
      You will be automatically subscribed to notification emails for this project. To change your email notification
      preferences, visit your project or your user settings:
	  <a href="${domain + "settings/notifications/"}">${domain}settings/notifications</a>
      </p>
    % endif
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
