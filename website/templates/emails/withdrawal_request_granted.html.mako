<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
        Dear ${contributor.fullname},<br>
        <br>
    % if not ever_public:
        % if is_requester:
            You have withdrawn your ${document_type} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name}.
            <br>
            The ${document_type} has been removed from ${reviewable.provider.name}.
            <br>
        % else:
            ${requester.fullname} has withdrawn your ${document_type} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name}.
            <br>
            The ${document_type} has been removed from ${reviewable.provider.name}.
            <br>
        % endif
    % else:
        % if is_requester:
            % if document_type == 'preprint':
                Your request to withdraw your preprint <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name} has been approved by the service moderators.
                <br>
                The registration has been removed from ${reviewable.provider.name}, but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
                <br>
            % else:
                Your request to withdraw your ${document_type} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> has been approved by ${reviewable.provider.name} moderators.
                % endif
        % elif force_withdrawal:

            A moderator has withdrawn your ${document_type} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name}.
            <br>
            % if document_type == 'preprint':
                The preprint has been removed from ${reviewable.provider.name}, but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
                <br>
            % endif
        % else:
            ${requester.fullname} has withdrawn your ${document_type} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name}.
            <br>
            The ${document_type} has been removed from ${reviewable.provider.name}, but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
            <br>
        % endif
    % if reviewable.withdrawal_justification:
        The moderator has provided the following comment:
        <br>
        ${comment}
        <br>
        The ${document_type} has been removed from ${reviewable.provider.name} but its metadata is still available: title of the withdrawn ${document_type}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
    % endif
        <br>
        Sincerely,<br>
        The ${reviewable.provider.name} and OSF Teams
        <br>
        <br>
        To change how often you receive emails, visit your <a href=${notification_settings}>user settings</a> to manage default email settings.

</tr>
</%def>
