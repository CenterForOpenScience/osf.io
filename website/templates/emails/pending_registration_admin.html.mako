<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    % if is_initiator:
      You have requested final approvals to submit your registration
      titled <a href="${registration_link}">${reviewable.title}</a>.
    % else:
      ${initiated_by} has requested final approvals to submit your registration
      titled <a href="${registration_link}">${reviewable.title}</a>.
    % endif
    </p>
    <p>
    % if is_moderated:
      If approved by all admin contributors, the registration will be submitted for moderator review.
      If the moderators approve, the registration will be made public as part of the
      ${reviewable.provider.name if reviewable.provider else 'OSF Registry'}.
    % else:
      If approved by all admin contributors, the registration will be made public as part of the
      ${reviewable.provider.name if reviewable.provider else 'OSF Registry'}.
    % endif
    </p>
    <p style="color:red;">
      You have ${approval_time_span} hours from midnight tonight (EDT) to approve or cancel
      this registration before it is automatically submitted.
    </p>
    <p>
    To approve this registration: <a href="${approval_link}">Click here</a>.<br>
    To cancel this registration: <a href="${disapproval_link}">Click here</a>.
    </p>
    <p>
    Note: If any admin clicks their cancel link, the submission will be cancelled immediately, and the
    pending registration will be reverted to draft state to revise and resubmit. This operation is irreversible.
    </p>
    % if reviewable.draft_registration.first() and not reviewable.draft_registration.first().has_project:
      <p>
      An <a href="${reviewable.registered_from.absolute_url}">OSF Project</a> was created from
	  this registration to support continued collaboration and sharing of your research.
      This project will remain available even if your registration is rejected.
      </p>
      <p>
      You will be automatically subscribed to notification emails for this project. To change your email notification
      preferences, visit your project or your user settings:
	  <a href="${settings.DOMAIN + "settings/notifications/"}">${settings.DOMAIN}settings/notifications</a>
      </p>
    % endif
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
