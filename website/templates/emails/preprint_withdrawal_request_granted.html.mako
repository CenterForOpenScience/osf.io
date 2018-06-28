<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
        Dear ${contributor.fullname},<br>
        <br>
    % if is_submitter:
        Your request to withdraw your ${preprint.provider.preprint_word} ${preprint.node.title} from ${preprint.provider.name} has been approved by the service moderators.
        <br>
        The ${preprint.provider.preprint_word} has been removed from ${preprint.provider.name}, but its metadata is still available: title of the withdrawn ${preprint.provider.preprint_word}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
        <br>
    % else:
        ${requester.fullname} has withdrawn your ${preprint.provider.preprint_word} ${preprint.node.title} from ${preprint.provider.name}.
        <br>
        The ${preprint.provider.preprint_word} has been removed from ${preprint.provider.name}, but its metadata is still available: title of the withdrawn ${preprint.provider.preprint_word}, its contributor list, abstract, tags, DOI, and reason for withdrawal (if provided).
        <br>
    % endif
        <br>
        Sincerely,<br>
        The ${preprint.provider.name} and OSF Teams
        <br>

</tr>
</%def>
