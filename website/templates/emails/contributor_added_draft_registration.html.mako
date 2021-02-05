<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>
    <p>
        ${'You just started' if not referrer_name else referrer_name + ' just added you to'}
        % if node.title == 'Untitled':
            <a href="${node.absolute_url}">a new registration draft</a>
        % else:
            a new registration draft titled <a href="${node.absolute_url}"> + ${node.title} </a>
        % endif
    </p>
    <p>
        It's <b>important</b> that you save or bookmark this email to return to your registration draft to make additional edits.
    </p>
    % if is_initiator or node.has_permission(contributor, 'admin'):
        <p>
            Each contributor that is added will be notified via email, which will contain a link to the drafted registration.
        </p>
    % endif
    % if not is_initiator:
        <p>
            If you have been erroneously associated with this registration draft, then you may visit the draft to remove yourself.
        </p>
    % endif
    <p>
        Sincerely,
    </p>
    <p>
        The OSF Team
    </p>
    <p>
        Want more information? Visit <a href="${settings.DOMAIN}">${settings.DOMAIN}</a> to learn about the OSF, or <a href="https://cos.io/" >https://cos.io/</a> for information about its supporting organization, the Center for Open Science.
    </p>
    <p>
        Questions? Email <a href="mailto: support@cos.io">support@cos.io</a>
    </p>
  </td>
</tr>
</%def>
