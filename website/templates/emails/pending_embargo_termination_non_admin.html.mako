<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    ${initiated_by} has requested final approvals to end the embargo for your registration
    titled <a href="${registration_link}">${reviewable.title}</a>
    </p>
    <p>
    If all admins contributors appove, the registration will be made public
	as part of the ${reviewable.provider.name} registry.
    </p>
    <p>
    Admins have ${approval_time_span} hours from midnight tonight (EDT) to approve or cancel this
    request before the embargo is automatically lifted and the registration is made public.
    </p>
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
    </p>
</tr>
</%def>
