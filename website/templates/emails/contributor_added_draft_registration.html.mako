<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},
    <p>
    ${'You just started' if not referrer_name else referrer_name + ' has added you as a contributor on'}
    % if not node.title or node.title == 'Untitled':
      <a href="${node.absolute_url}">a new registration draft</a>
    % else:
      a new registration draft titled <a href="${node.absolute_url}">${node.title}</a>
    % endif
    to be submitted for inclusion in the
	<a href="${settings.DOMAIN}/registries/${node.provider._id if node.provider else 'osf'}">${node.provider.name if node.provider else "OSF Registry"}</a>.
    </p>
    <p>
    You can access this draft by going to your <a href="${settings.DOMAIN}registries/my-registrations?tab=drafts">"My Registrations" page.</a>
    </p>
    % if node.has_permission(user, 'admin'):
      <p>
      Each contributor that is added will be notified via email, which will contain a link to the draft registration.
      </p>
    % endif
    % if referrer_name:
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
    Want more information? Visit <a href="${settings.DOMAIN}">${settings.DOMAIN}</a> to learn about the OSF,
    or <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization,
    the Center for Open Science.
    </p>
    <p>
    Questions? Email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>
    </p>
  </td>
</tr>
</%def>
