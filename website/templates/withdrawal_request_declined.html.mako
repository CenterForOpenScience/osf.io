<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
        % if document_type == 'registration':
            Dear ${contributor_fullname},
		    <p>
            Your request to withdraw your registration <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name} has been declined by the service moderators. The registration is still publicly available on ${reviewable_provider_name}.
			<p>
            % if notify_comment:
                The moderator has provided the following comment:<br>
                ${comment}
            % endif
        % else:
            Dear ${requester_fullname},
            <p>
            Your request to withdraw your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name} has been declined by the service moderators. Login and visit your ${document_type} to view their feedback. The ${document_type} is still publicly available on ${reviewable_provider_name}.
        % endif
        <p>
        Sincerely,<br>
        The ${reviewable_provider_name} and OSF Teams<br>
</tr>
</%def>
