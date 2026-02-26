<%inherit file="notify_base.mako" />

<%def name="content()">
    <tr>
      <td style="border-collapse: collapse;">
        Hello ${recipient_fullname},
        <p>
            This message is coming from an Institutional administrator within your Institution.
        </p>
        % if message_text:
        <p>
            ${message_text}
        </p>
        % endif
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
