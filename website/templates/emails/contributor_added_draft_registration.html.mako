<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>

    ${'You just started' if not referrer_name else referrer_name + ' just added you to'}  a new registration draft titled <a href="${node.absolute_url}">${node.title if node.title else 'new registration draft'}</a>
    <p>
        It's important that you save or bookmark this email to return to your registration draft to make additional edits.
    </p>
    <p>
        % if is_initiator or node.has_permission(contributor, 'admin'):
            Each contributor that is added will be notified via email, which will contain a link to the drafted registration.
        % endif
    </p>
    <p>
        % if not is_initiator:
            If you have been erroneously associated with this registration draft, then you may visit the draft to remove yourself.
        % endif
    </p>
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
        Questions? Email contact@osf.io
    </p>
  </td>
</tr>
</%def>
