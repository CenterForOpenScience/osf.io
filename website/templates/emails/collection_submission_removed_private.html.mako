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
            You have changed the privacy of <a href="${node.absolute_url}">${node.title}</a> and it has therefore been
            removed from
            % if collection.provider:
                <a href="${settings.DOMAIN + 'collections/' + collection.provider._id}">${collection.provider.name}</a>
            % else:
                <a href="${settings.DOMAIN + 'myprojects/'}">${collection.provider.name}</a>
            % endif
            . If you wish to be associated with the collection, you will need to request addition to the collection again.
        % else:
            <a href="${remover.absolute_url}">${remover.fullname}</a> has changed the privacy settings for
            <a href="${node.absolute_url}">${node.title}</a> it has therefore been removed from
            % if collection.provider:
                <a href="${settings.DOMAIN + 'collections/' + collection.provider._id}">${collection.provider.name}</a>
            % else:
                <a href="${settings.DOMAIN + 'myprojects/'}">${collection.provider.name}</a>
            % endif
            It will need to be re-submitteds to be included in the collection again.
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
