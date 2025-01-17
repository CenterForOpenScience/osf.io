<%inherit file="notify_base.mako" />

<%def name="content()">
    <tr>
      <td style="border-collapse: collapse;">
        <%!from website import settings%>
        Hello ${recipient.fullname},
        <p>
            <a href="${sender.absolute_url}">${sender.fullname}</a> has requested access to <a href="${node.absolute_url}">${node.title}</a>.
        </p>
        % if comment:
        <p>
            ${comment}
        </p>
        % endif
        <p>
            To review the request, click <a href="${node.absolute_url}/contributors/">here</a> to allow or deny access and configure permissions.
        </p>
        <p>
            This request is being sent to you because your project has the “Request Access” feature enabled.
            This allows potential collaborators to request to be added to your project or to disable this feature, click
            <a href="${node.absolute_url}/settings/">here</a>
        </p>

        <p>
            Want more information? Visit <a href="${settings.DOMAIN}">${settings.DOMAIN}</a> to learn about OSF, or
            <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization, the Center
            for Open Science.
        </p>
        <p>
            Questions? Email <a href="mailto:${settings.OSF_CONTACT_EMAIL}">${settings.OSF_CONTACT_EMAIL}</a>
        </p>
      </td>
    </tr>
</%def>
