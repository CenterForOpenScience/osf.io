<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    The proposed updates to your Registration
    <a href="${response.parent.absolute_url}">${response.parent.title}</a> have been approved.
	<p>
    The updated responses will be visible by default to all viewers of the registration
    along with the reason for the changes. All previously approved updates will remain accessible
    for comparrison through the "Updates" dropdown on the Registration overview page.
	<p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
