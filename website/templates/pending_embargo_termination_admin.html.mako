<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    % if is_initiator:
      You have requested final approvals to end the embargo for your registration
      titled <a href="${registration_link}">${reviewable_title}</a>
    % else:
      ${initiated_by_fullname} has requested final approvals to end the embargo for your registration
      titled <a href="${registration_link}">${reviewable_title}</a>
    % endif
    </p>
    <p>
    If all admin contributors approve, the registration will be made public as part of the
<<<<<<< HEAD:website/templates/pending_embargo_termination_admin.html.mako
    <a href="${domain}/registries/${reviewable_provider__id if reviewable_provider__id else 'osf'}">${reviewable_provider_name if reviewable_provider__id else "OSF Registry"}</a>.
=======
    <a href="${settings.DOMAIN}/registries/${reviewable.provider._id if reviewable.provider else 'osf'}">${reviewable.provider.name if reviewable.provider else "OSF Registry"}</a>.
>>>>>>> upstream/hotfix/25.18.1:website/templates/emails/pending_embargo_termination_admin.html.mako
    </p>
    <p style="color:red;">
    You have ${approval_time_span} hours from midnight tonight (EDT) to approve or cancel this
    request before the embargo is lifted and the registration is made public.
    </p>
    <p>
    To approve this request: <a href="${approval_link}">Click here</a>.<br>
    To cancel this request: <a href="${disapproval_link}">Click here</a>
    </p>
    <p>
    Note: If any admin clicks their cancel link, the embargo termination request will
    be cancelled immediately and the registration will remain private until its current
    embargo expires.
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
