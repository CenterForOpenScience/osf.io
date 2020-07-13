<%inherit file="notify_base.mako" />

<%def name="content()">
<%!
    from website import settings
%>
${_(u'''<tr>
  <td style="border-collapse: collapse;">
    Hello %(adminFullname)s,<br>
    <br>
    <a href="${requester.absolute_url}">%(requesterFullname)s</a> has requested access to your ${%(projectOrComponent)s} "<a href="%(absoluteUrl)s">%(title)s</a>."<br>
    <br>
    To review the request, click <a href="%(contributorUrl)s">here</a> to allow or deny access and configure permissions.<br>
    <br>
    This request is being sent to you because your project has the 'Request Access' feature enabled. This allows potential collaborators to request to be added to your project. To disable this feature, click <a href="%(projectSettingsUrl)s">here</a>.<br>
    <br>
    Sincerely,<br>
    <br>
    The GRDM Team<br>
    <br>
    Want more information? Visit %(rdmUrl)s to learn about GRDM, or %(niiHomepageUrl)s for information about its supporting organization, the %(niiFormalnameEn)s.<br>
    <br>
    Questions? Email %(osfContactEmail)s<br>


</tr>''') % dict(adminFullname=admin.fullname, requesterFullname=requester.fullname, projectOrComponent=node.project_or_component, absoluteUrl=node.absolute_url, title=node.title, contributorUrl=contributors_url, projectSettingsUrl=project_settings_url, rdmUrl=settings.RDM_URL, niiHomepageUrl=settings.NII_HOMEPAGE_URL, niiFormalnameEn=settings.NII_FORMAL_NAME_EN, niiFormalnameJa=settings.NII_FORMAL_NAME_JA, osfContactEmail=osf_contact_email)}
</%def>
