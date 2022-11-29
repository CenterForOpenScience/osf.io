<%inherit file="notify_base.mako" />
<%!
    from website import settings
%>
<%def name="content()">
    <tr>
      <td style="border-collapse: collapse;">
        Hello ${user.fullname},<br>
        <br>
        <p>
            % if is_initator:
                You just started to a request to add <a href="${node.absolute_url}">${node.title}</a>
                to <a href="${settings.DOMAIN.rstrip('/') + collection.url}">${collection.title}</a>. Each Admin  contributor will be notified via
                email.
            % elif is_registered_contrib:
                 <a href="${submitter.absolute_url}">${submitter.fullname}</a> just included you in <a href="${node.absolute_url}">${node.title}</a> to a request to add
                  <a href="${node.absolute_url}">${node.title}</a> to
                  <a href="${settings.DOMAIN.rstrip('/') + collection.url}">${collection.title}</a>. Each Admin  contributor will be notified via
                  email.
            % else:
                <a href="${submitter.absolute_url}">${submitter.fullname}</a> included you in a request to add
                <a href="${node.absolute_url}">${node.title}</a> to <a href="${settings.DOMAIN.rstrip('/') + collection.url}">${collection.title}</a>
                <a href="${claim_url}">$Click here to claim account link</a>. After you set a password, you will be able to make
                contributions to the project. You will also be able to easily access this and any other project or
                component by going to your "My Projects" page. If you decide to not make an account, then it's <b>important
                </b> that you save or bookmark this email.
            % endif
        </p>
        <p>
            If you have been erroneously associated with this project or component, then you may visit its contributor
            section to remove yourself then email ${osf_contact_email}.
        </p>
        Sincerely,<br>
        <br>
        The OSF Team<br>
        <br>
        Want more information? Visit https://osf.io/ to learn about OSF, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
        <br>
        Questions? Email ${osf_contact_email}<br></tr>
    </tr>
</%def>
