<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
        The Quick Files feature has been discontinued and your files have been migrated into an OSF Project.  You can find the new Project on your My Projects page, entitled “<name>’s Quick Files”.  Your favorite Quick Files features are still present; you can view, download, and share your files from their new location.  Your file URL’s will also continue to resolve properly, and you can still move your files between Projects by linking your Projects.  Contact support@osf.io if you have any questions or concerns.
    </p>
    <p>
        Thank you for partnering with us as a stakeholder in open science and in the success of the infrastructure that help make it possible.
    </p>
    <p>
        The Center for Open Science Team
    </p>
    <p>
        Sincerely,<br>
        The OSF Team
    </p>
    <p>
        Want more information? Visit <a href="${settings.DOMAIN}">${settings.DOMAIN}</a> to learn about the OSF,
        or <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization,
        the Center for Open Science.
    </p>
    <p>
        Questions? Email <a href="mailto:${settings.OSF_CONTACT_EMAIL}">${settings.OSF_CONTACT_EMAIL}</a>
    </p>
  </td>
</tr>
</%def>
