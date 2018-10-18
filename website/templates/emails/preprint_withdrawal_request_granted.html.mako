<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
        Dear ${contributor.fullname},<br>
        <br>
    % if is_requester:
        Your request to withdraw your ${reviewable.provider.preprint_word} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name} has been approved by the service moderators.
        <br>
        The ${reviewable.provider.preprint_word} has been removed from ${reviewable.provider.name}, but its metadata is still available: title of the withdrawn ${reviewable.provider.preprint_word}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
        <br>
    % elif withdrawal_submitter_is_moderator_or_admin:
        A moderator has withdrawn your ${reviewable.provider.preprint_word} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name}.
        <br>
        The ${reviewable.provider.preprint_word} has been removed from ${reviewable.provider.name}, but its metadata is still available: title of the withdrawn ${reviewable.provider.preprint_word}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
        <br>
    % else:
        ${requester.fullname} has withdrawn your ${reviewable.provider.preprint_word} <a href="${reviewable.absolute_url}">"${reviewable.title}"</a> from ${reviewable.provider.name}.
        <br>
        The ${reviewable.provider.preprint_word} has been removed from ${reviewable.provider.name}, but its metadata is still available: title of the withdrawn ${reviewable.provider.preprint_word}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
        <br>
    % endif
        <br>
        Sincerely,<br>
        The ${reviewable.provider.name} and OSF Teams
        <br>

</tr>
</%def>
