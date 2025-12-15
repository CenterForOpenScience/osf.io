<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user_fullname},
    <p>
    ${initiated_by_fullname} has requested final approvals to end the embargo for your registration
    titled <a href="${registration_link}">${reviewable_title}</a>
    </p>
    <p>
<<<<<<< HEAD:website/templates/pending_embargo_termination_non_admin.html.mako
    If all admins contributors appove, the registration will be made public as part of the
    <a href="${domain}/registries/${reviewable_provider__id if reviewable_provider__id else 'osf'}">${reviewable_provider_name if reviewable_provider__id else "OSF Registry"}</a>.
=======
    If all admins contributors approve, the registration will be made public as part of the
    <a href="${settings.DOMAIN}/registries/${reviewable.provider._id if reviewable.provider else 'osf'}">${reviewable.provider.name if reviewable.provider else "OSF Registry"}</a>.
>>>>>>> upstream/hotfix/25.18.1:website/templates/emails/pending_embargo_termination_non_admin.html.mako
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
