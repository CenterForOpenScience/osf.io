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
             The request to add <a href="${node.absolute_url}">${node.title}</a> to
             % if collection.provider:
                <a href="${settings.DOMAIN + 'collections/' + collection.provider._id}">${collection.provider.name}</a>
            % else:
                <a href="${settings.DOMAIN + 'myprojects/'}">${collection.provider.name}</a>
            % endif

            was canceled. If you wish to be associated with the collection, you will need to request to be added again.
        % else:
            <a href="${remover.absolute_url}">${remover.fullname}</a> canceled the request to add
            <a href="${node.absolute_url}">${node.title}</a>to
            % if collection.provider:
                <a href="${settings.DOMAIN + 'collections/' + collection.provider._id}">${collection.provider.name}</a>
            % else:
                <a href="${settings.DOMAIN + 'myprojects/'}">${collection.provider.name}</a>
            % endif
            If you wish to be associated with the collection, an admin will need to request addition again.
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
