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
      If the moderators approve, the registration will be embargoed until
      ${embargo_end_date.date()}, at which time it will be made public as part of the
      <a href="${settings.DOMAIN}/registries/${reviewable.provider._id if reviewable.provider else 'osf'}">${reviewable.provider.name if reviewable.provider else "OSF Registry"}</a>.
    % else:
      If approved by all admin contributors, the registration will be embargoed until
      ${embargo_end_date.date()}, at which point it will be made public as part of the
      <a href="${settings.DOMAIN}/registries/${reviewable.provider._id if reviewable.provider else 'osf'}">${reviewable.provider.name if reviewable.provider else "OSF Registry"}</a>.
    % endif
    </p>
    <p style="color:red;">
    You have ${approval_time_span} hours from midnight tonight (EDT) to approve or cancel
    this registration before it is automatically submitted.
    </p>
    <p>
    To approve this embargoed registration: <a href="${approval_link}">Click here</a>.<br>
    To cancel this embargoed registration: <a href="${disapproval_link}">Click here</a>.
    </p>
    <p>
    % if not reviewable.provider or reviewable.provider._id != 'gfs':
        Note: If any admin clicks their cancel link, the submission will be canceled immediately, and the
        pending registration will be reverted to draft state to revise and resubmit. This operation is irreversible.
    % else:
        Please note:
        <ul>
            <li>
                If any admin clicks their cancel link, the submission will be cancelled immediately, and the
                pending registration will be reverted to draft state to revise and resubmit. This operation is irreversible.
            </li>
            <li>
                You are an administrator on a registration submitted to the GFS registry, <b>by approving this registration submission</b>
                (or allowing 48 hours to pass) <b>you agree to receive communications from COS staff</b> about the registration, study data,
                and your experience with the GFS project. Your personal information will not be shared beyond COS staff with
                the explicit purpose of communication regarding access to GFS study data.
            </li>
            <li>
                By rejecting this registration submission you are thereby not agreeing to receive communications about the
                registration, study data, and your experience with the GFS project.
            </li>
            <li>
                If you do not feel comfortable agreeing to these terms to gain access to the GFS study data, you may contact
                <a href= "mailto: globalflourishing@cos.io">globalflourishing@cos.io</a> to discuss your concerns.
            </li>
    % endif
    </p>
    % if not reviewable.branched_from_node:
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
    % if not reviewable.provider or reviewable.provider._id != 'gfs':
        The OSF Team<br>
    % else:
        COS and Global Flourishing Study<br>
    % endif
</tr>
</%def>
