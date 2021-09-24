<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    Your ${resource_type} <a href="${parent_url}">"${title}"</a> has updates that are
    pending approval.
    <p>
    You can review the updated responses by clicking <a href="${update_url}">here</a>.
    % if is_approver:
        From that page, You will be able to either approve the updates or request further changes.
    % endif
    <p>
    %if resposne.is_moderated:
    If the proposed updates are approved by all "admin" users on the ${resource_type},
    they will be submitted for moderator review.
    %endif
    Once the updates have received all required approvals, the updated responses and the
    reason for the changes will be visible by default for all users viewing your ${resource_type}.
    All previously approved updates will remain accessible for comparrison through the
    "Updates" dropdown on the main ${resource_type} page.
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
