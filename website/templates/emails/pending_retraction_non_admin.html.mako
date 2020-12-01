<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    We just wanted to let you know that ${initiated_by} has requested a withdrawal for the following registration: ${registration_link}.<br>
    <br>
    If approved

    % if is_moderated:
         by project admins, a withdrawal request will be sent to ${reviewable.provider.name} moderators for review.
    % else:
        , the registration will be marked as withdrawn. Its content will be removed from the OSF, but leave basic
        metadata behind. The title of a withdrawn registration and its contributor list will remain, as will
        justification or explanation of the withdrawal, if provided.<br>
    % endif
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robots<br>

</tr>
</%def>
