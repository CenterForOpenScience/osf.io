<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${fullname},
    <p>
    ${referrer.fullname} has added you as a contributor on
    % if node.title == 'Untitled':
      <a href="${node.absolute_url}">a new registration draft</a>
    % else:
      a new registration draft titled <a href="${node.absolute_url}">${node.title}</a>
    % endif
    to be submitted for inclusion in the ${node.provider.name} registry.
    </p>
    <p>
    <a href="${claim_url}">Click here</a> To set a password for your account.
    <\p>
    <p>
    Once you have set a password, you will be able to this registration draft as well as create
    your own projects, registrations, and preprints on the OSF. You will be able to access this draft
    by going to your <a href="${settings.DOMAIN}registries/my-registrations">"My Registrations" page.</a>
    <\p>
    <p>
    If you are not ${fullname} or if you have been erroneously associated with "${node.title}" then
    email ${osf_contact_email} with the subject line "Claiming Error" to report the problem.
    <\p>
    <p>
    Sincerely,
    <p>
    Open Science Framework Robot
    <p>
    Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or
    https://cos.io/ for information about its supporting organization, the Center for Open Science.
    <p>
    Questions? Email ${osf_contact_email}
</tr>
</%def>
