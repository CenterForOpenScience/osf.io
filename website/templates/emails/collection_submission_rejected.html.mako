<%inherit file="notify_base.mako" />
%>
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},<br>
    <br>
    <p>
        % if is_admin:
            Your request to add  <a href="${node.absolute_url}">${node.title}</a> to
            <a href="${domain + 'collections/' + collection_provider__id}">${collection_provider_name}</a> was not accepted.
            <p>
                Rejection Justification:
            </p>
            <p>
                ${rejection_justification}
            </p>
        % else:
            <a href="${node.absolute_url}">${node.title}</a> was not accepted  by <a href="${domain + 'collections/' + collection_provider__id}">${collection.provider.name}</a>.
        % endif
    </p>
    <p>
        If you are not ${user_fullname} or you have been erroneously associated with
        <a href="${node_absolute_url}">${node.title}</a>, email ${osf_contact_email} with the subject line
        "Claiming error" to report the problem.
    </p>
    Sincerely,<br>
    <br>
    The OSF Team<br>
    <br>
    Want more information? Visit https://osf.io/ to learn about OSF, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email ${osf_contact_email}<br></tr>
</%def>
