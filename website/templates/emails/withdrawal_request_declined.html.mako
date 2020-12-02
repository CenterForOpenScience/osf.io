<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
        % if document_type == 'registration':
            Your request to withdraw your registration <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name} has been declined by the service moderators. The registration is still publically available on ${reviewable.provider.name}.

            % if notify_comment:
                The moderator has provided the following comment:
                <br>

                ${comment}

            % endif
        % else:
            Dear ${requester.fullname},<br>
            <br>
            Your request to withdraw your ${document_type} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name} has been declined by the service moderators. Login and visit your ${document_type} to view their feedback. The ${document_type} is still publicly available on ${reviewable.provider.name}.
            <br>
            Sincerely,<br>
            The ${reviewable.provider.name} and OSF Teams
            <br>
        % endif
        <br>
        Sincerely,<br>
        The ${reviewable.provider.name} and OSF Teams
        <br>

</tr>
</%def>
