<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    % if is_initiator:
    You initiated a registration of your project ${project_name}. The proposed registration can be viewed here: ${registration_link}.<br>
    % else:
    ${initiated_by} has initiated a registration of your project ${project_name}. The proposed registration can be viewed here: ${registration_link}.<br>
    % endif
    <br>
    If approved, a registration will be created for the project and will be made public immediately
    % if is_moderated:
         and sent to ${reviewable.provider.name} moderators for review
    % endif
    .
    <br>
    <br>
    To approve this registration, click the following link: <a href="${approval_link}">Click here</a><br>
    <br>
    To cancel this registration, click the following link: <a href="${disapproval_link}">Click here</a><br>
    <br>
    % if is_moderated:
        Note: Clicking the cancel link will immediately cancel the pending registration and the
        registration will remain in draft state.
        If you neither approve nor cancel the registration within ${approval_time_span} hours from
        midnight tonight (EDT) the registration will be automatically approved and
         sent to ${reviewable.provider.name} moderators for review.
    % else:
        If you neither approve nor cancel the registration within ${approval_time_span} hours from midnight tonight (EDT) the registration will be automatically approved and made public.
    % endif
    <br>


    Note: Clicking the cancel link will immediately cancel the pending registration and the<br>
    registration will remain in draft state. If you neither approve nor cancel the registration<br>
    within ${approval_time_span} hours from midnight tonight (EDT) the registration will be<br>
    automatically approved and made public. This operation is irreversible.If you neither approve
    nor cancel the registration within ${approval_time_span} hours from midnight tonight (EDT)
     the registration will be automatically approved and made public.
     % if is_moderated:
      and sent to ${reviewable.provider.name} moderators for review.
    % endif


    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robots<br>


</tr>
</%def>
