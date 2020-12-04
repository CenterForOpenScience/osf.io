<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    We just wanted to let you know that ${initiated_by} has initiated the following pending registration: ${registration_link}.
    <p>
    % if is_moderated:
        If approved by project admins, the registration will be created and sent to ${reviewable.provider.name} moderators for review.
    % else:
        If approved, a registration will be created for the project, viewable here: <a href="${registration_link}">Click here</a>, and it will remain
        public until it is withdrawn.
    % endif
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
