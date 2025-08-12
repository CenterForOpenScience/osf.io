<%inherit file="notify_base.mako" />
<%def name="content()">
    <tr>
      <td style="border-collapse: collapse;">
        Hello ${user_fullname},<br>
        <br>
        <p>
            % if is_initator:
                You just started a request to add <a href="${node_absolute_url}">${node_title}</a>
                to <a href="${collections_link}">${collection_provider_name}</a>.
                All admins and contributors will be notified via email.
            % elif is_registered_contrib:
                 <a href="${submitter_absolute_url}">${submitter_fullname}</a> just included you in <a href="${node_absolute_url}">${node_title}</a> to a request to add
                  <a href="${node_absolute_url}">${node_title}</a> to
                  <a href="${collections_link}">${collection_provider_name}</a>.
                  All admins and contributors will be notified via email.
            % else:
                <a href="${submitter_absolute_url}">${submitter_fullname}</a> included you in a request to add
                <a href="${node_absolute_url}">${node_title}</a> to <a href="${collections_link}">${collection_provider_name}</a>
                <a href="${claim_url}">Click here to claim account link</a>. After you set a password, you will be able to make
                contributions to the project. You will also be able to easily access this and any other project or
                component by going to your "My Projects" page. If you decide to not make an account, then it's <b>important
                </b> that you save or bookmark this email.
            % endif
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
