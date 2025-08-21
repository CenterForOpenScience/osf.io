<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
        Dear ${contributor_fullname},
        <p>
    % if document_type == 'registration':
        % if force_withdrawal:
            A moderator has withdrawn your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name}.
        % else:
            Your request to withdraw your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> has been approved by ${reviewable_provider_name} moderators.
        % endif
        % if comment and notify_comment:
            <p>
            The moderator has provided the following comment:<br>
            ${comment}
        % endif
        <p>
        The ${document_type} has been removed from ${reviewable_provider_name}, but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
    % else:
        % if not ever_public:
            % if is_requester:
                You have withdrawn your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name}.
                <br>
                The ${document_type} has been removed from ${reviewable_provider_name}.
                <br>
            % else:
                ${requester_fullname} has withdrawn your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name}.
                % if reviewable.withdrawal_justification:
                    ${requester_fullname} provided the following justification: "${reviewable+withdrawal_justification}"
                % endif
                <br>
                The ${document_type} has been removed from ${reviewable_provider_name}.
                <br>
            % endif
        % else:
            % if is_requester:
                Your request to withdraw your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name} has been approved by the service moderators.
                <br>
                The ${document_type} has been removed from ${reviewable_provider_name}, but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
                <br>
            % elif force_withdrawal:
                A moderator has withdrawn your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name}.
                <br>
                The ${document_type} has been removed from ${reviewable_provider_name}, but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, and DOI.
                % if reviewable.withdrawal_justification:
                    The moderator has provided the following justification: "${reviewable_withdrawal_justification}".
                    <br>
                % endif
                <br>
            % else:
                ${requester_fullname} has withdrawn your ${document_type} <a href="${reviewable_absolute_url}">"${reviewable_title}"</a> from ${reviewable_provider_name}.
                <br>
                The ${document_type} has been removed from ${reviewable_provider_name}, but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, and DOI.
                % if reviewable_withdrawal_justification:
                    ${requester_fullname} provided the following justification: "${reviewable_withdrawal_justification}".
                    <br>
                % endif
                <br>
            % endif
        % endif
    % endif
        <p>
        Sincerely,<br>
        The ${reviewable_provider_name} and OSF Teams
</tr>
</%def>
