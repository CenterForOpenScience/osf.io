<%inherit file="notify_base.mako" />

<%def name="content()">
    <tr>
      <td style="border-collapse: collapse;">
        <%!from website import settings%>
        Hello ${recipient.fullname},
        <p>
            ${sender.fullname} from your <b>${institution.name}</b>, has sent you a request regarding your project.
        </p>
        % if message_text:
        <p>
            Message from ${sender.fullname}:<br>
            ${message_text}
        </p>
        % endif
        <p>
            To review this request, please visit your project dashboard or contact your institution administrator for further details.
        </p>
        <p>
            Sincerely,<br>
            The OSF Team
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
