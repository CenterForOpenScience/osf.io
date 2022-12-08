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
        % if is_admin:
            <a href="${node.absolute_url}">${node.title}</a> was  removed by <a href="${settings.DOMAIN + 'collections/' + collection.provider._id}">${collection.title}</a>:
            <br>
            <p>
                ${rejection_justification}
            </p>
            This can also be viewed in the collection status section on the project or component page.
            If you wish to be associated with the collection, you will need to reapply to the collection again.
        % else:
            <a href="${node.absolute_url}">${node.title}</a> was removed by
            <a href="${settings.DOMAIN + 'collections/' + collection.provider._id}">${collection.title}</a>
        % endif
    </p>
    <p>
        If you are not ${user.fullname} or you have been erroneously associated with
        <a href="${node.absolute_url}">${node.title}</a>, email ${osf_contact_email} with the subject line
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
