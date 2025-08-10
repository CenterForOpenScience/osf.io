<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},
    <p>
    ${referrer_fullname} has added you as a contributor on
    % if not node.title or node.title == 'Untitled':
      <a href="${node.absolute_url}">a new registration draft</a>
    % else:
      a new registration draft titled <a href="${node_absolute_url}">${node.title}</a>
    % endif
    to be submitted for inclusion in the
	<a href="${domain}/registries/${node_provider__id if node.provider else 'osf'}">${registry_text}</a>.
    </p>
    <p>
    <a href="${claim_url}">Click here</a> to set a password for your account.
    </p>
    <p>
    Once you have set a password, you will be able to contribute to this registration draft as well as
	create your own projects, registrations, and preprints on the OSF. You will be able to access this draft
    by going to your <a href="${domain}registries/my-registrations?tab=drafts">"My Registrations" page.</a>
    </p>
    <p>
    If you are not ${user_fullname} or if you have been erroneously associated with
    % if not node.title or node.title == 'Untitled':
	  this registration draft
    % else:
      "${node_title}"
	% endif
    email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a> with the subject line
    "Claiming Error" to report the problem.
    </p>
    <p>
    Sincerely,
    <p>
    The OSF Team
    <p>
    Want more information? Visit <a href="${domain}">${domain}</a> to learn about the OSF,
    or <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization,
    the Center for Open Science.
    <p>
    Questions? Email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>
</tr>
</%def>
