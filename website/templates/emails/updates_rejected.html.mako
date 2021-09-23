<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    Further changes have been requested for the proposed updates to your Registration
	<a href="${response.parent.absolute_url}">${response.parent.title}</a>.
	<p>
    You can view and contribute to the updates in-progress by clicking
    <a href="${response.osf_url}">here</a>.
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
