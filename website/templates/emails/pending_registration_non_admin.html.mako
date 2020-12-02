<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    We just wanted to let you know that ${initiated_by} has initiated the following pending registration: ${registration_link}.<br>
    <br>
    If approved
    % if is_moderated:
         by project admins, the registration will be created and sent to ${reviewable.provider.name} moderators for review.
    % else:
        , a registration will be created for the project, viewable here: <a href="${registration_link}">Click here</a>, and it will remain
        public until it is withdrawn.
    % endif
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robots<br>

</tr>
</%def>
