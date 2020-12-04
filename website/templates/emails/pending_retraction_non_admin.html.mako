<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    We just wanted to let you know that ${initiated_by} has requested a withdrawal for the following registration: ${registration_link}.
    <p>
    % if is_moderated:
        If approved by project admins, a withdrawal request will be sent to ${reviewable.provider.name} moderators for review.
    % else:
        If approved, the registration will be marked as withdrawn. Its content will be removed from the OSF, but leave basic
        metadata behind. The title of a withdrawn registration and its contributor list will remain, as will
        justification or explanation of the withdrawal, if provided.
    % endif
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
