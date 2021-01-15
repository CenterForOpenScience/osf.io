<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name} has added you to a new registration draft here:
    <a href="${node.absolute_url}">${node.title if node.title else 'new registration draft'}</a>.
    <p>
        Contact the registration initiator if you were mistakenly associated with this registration.
    </p>
</tr>
</%def>
