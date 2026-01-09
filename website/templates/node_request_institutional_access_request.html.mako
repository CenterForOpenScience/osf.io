<%inherit file="notify_base.mako" />

<%def name="content()">
    <tr>
      <td style="border-collapse: collapse;">
        Hello ${recipient_fullname},
        <p>
            <a href="${sender_absolute_url}">${sender_fullname}</a> has requested access to <a href="${node_absolute_url}">${node_title}</a>.
        </p>
        % if comment:
        <p>
            ${comment}
        </p>
        % endif
        <p>
            To review the request, click <a href="${node_absolute_url}contributors/">here</a> to allow or deny access and configure permissions.
        </p>
        <p>
            This request is being sent to you because your project has the “Request Access” feature enabled.
            This allows potential collaborators to request to be added to your project or to disable this feature, click
            <a href="${node_absolute_url}settings/">here</a>
        </p>

        <p>
            Want more information? Visit <a href="${domain}">${domain}</a> to learn about OSF, or
            <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization, the Center
            for Open Science.
        </p>
        <p>
            Questions? Email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>
        </p>
      </td>
    </tr>
</%def>
