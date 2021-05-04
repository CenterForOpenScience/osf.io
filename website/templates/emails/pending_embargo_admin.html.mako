<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    % if is_initiator:
        You have requested final approvals to submit your registration titled <a href="${registration_link}">${reviewable.title}</a>.
    % else:
        ${initiated_by} has requested final approvals to submit your registration titled <a href="${registration_link}">${reviewable.title}</a>.
    % endif
	</p>
	<p>
    % if is_moderated:
		If approved by all admin contributors, the registration will be submitted for moderator review.
		If the moderators approve, the registration will be embargoed until ${embargo_end_date.date()},
        at which point it will be made public as part of the {reviewable.provider.name} registry.
    % else:
        If approved by all admin contributors, the registration will be embargoed until ${embargo_end_date.date()},
		at which point it will be made public as part of the {reviewable.provider.name} registry.
    % endif
	</p>
    <p style="color:red;">
	You have 48 hours from midnight tonight to approve or cancel this registration before it is automatically submitted
	</p>
    <p>
    Approve this embargoed registration: <a href="${approval_link}">Click here</a>.<br>
    Cancel this embargoed registration: <a href="${disapproval_link}">Click here</a>.
	</p>
    <p>
    Note: If any admin clicks their cancel link, the submission will be cancelled immediately, and the
	pending registration will be reverted to draft state to revise and resubmit. This operation is irreversible.
	</p>
	% if not reviewable.branched_from_node:
		<p>
		An OSF Project was created from this registration to support continued collaboration and sharing of your research.
		This project will remain available even if your registration is rejected.
		</p>
		<p>
		You will be automatically subscribed to notification emails for this project. To change your email notification
		preferences, visit your project or your user settings: https://staging2.osf.io/settings/notifications/
		</p>
	% endif
	<p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
