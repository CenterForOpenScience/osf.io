<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    Further changes have been requested for the proposed updates to your ${resource_type}
    <a href="${parent_url}">"${title}"</a>.
    <p>
    % if can_write:
        You can view and contribute to the updates in-progress by clicking
        <a href="${update_url}">here</a>.
    % else:
        You can view the updates in-progress by clicking <a href="${update_url}">here</a>.
    % endif
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
