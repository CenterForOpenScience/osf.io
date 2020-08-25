<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
        Dear ${requester.fullname},<br>
        <br>
        Your request to withdraw your ${reviewable.provider.preprint_word} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name} has been declined by the service moderators. Login and visit your ${reviewable.provider.preprint_word} to view their feedback. The ${reviewable.provider.preprint_word} is still publicly available on ${reviewable.provider.name}.
        <br>
        Sincerely,<br>
        The ${reviewable.provider.name} and OSF Teams
        <br>

</tr>
</%def>
