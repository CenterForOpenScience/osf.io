<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    ${referrer_text}
    % if not node_title or node_title == 'Untitled':
      <a href="${node_absolute_url}">a new registration draft</a>
    % else:
      to a new registration draft titled <a href="${node_absolute_url}">${node_title}</a>
    % endif
    to be submitted for inclusion in the
	<a href="${domain}/registries/${node_provider__id}">${registry_text}</a>.
    </p>
    <p>
    You can access this draft by going to your <a href="${domain}registries/my-registrations?tab=drafts">"My Registrations" page.</a>
    </p>
    % if node_has_permission_admin:
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
    Want more information? Visit <a href="${domain}">${domain}</a> to learn about the OSF,
    or <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization,
    the Center for Open Science.
    </p>
    <p>
    Questions? Email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>
    </p>
  </td>
</tr>
</%def>
