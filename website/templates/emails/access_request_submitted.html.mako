<%inherit file="notify_base.mako" />

<%def name="content()">
${_(u'''<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、%(adminFullname)sさん<br>
    <br>
    <a href="%(requesterAbsoluteUrl)s">%(requesterFullname)s</a>から、あなたの${u'プロジェクト' if node.project_or_component == 'project' else u'コンポーネント'}(<a href="%(nodeAbsoluteUrl)s">%(title)s</a>)へのアクセス申請がありました。<br>
    <br>
    申請をレビューするには<a href="%(contributorUrl)s">こちら</a>をクリックしてください。アクセスの許可/拒否および権限設定ができます。<br>
    <br>
    あなたのプロジェクトで「アクセス申請」の機能が有効になっているために申請が送られています。共同作業を希望する人がいれば、この機能を使ってあなたのプロジェクトに参加させることができます。機能を無効化するには<a href="%(projectSettingsUrl)s">こちら</a>をクリックしてください。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
    GakuNin RDMチーム<br>
    <br>
    GakuNin RDMの詳細については %(rdmUrl)s を、%(niiFormalnameJa)sについては %(niiHomepageUrl)s をご覧ください。<br>
    <br>
    メールでのお問い合わせは %(osfContactEmail)s までお願いいたします。<br>


</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello %(adminFullname)s,<br>
    <br>
    <a href="%(requesterAbsoluteUrl)s">%(requesterFullname)s</a> has requested access to your %(projectOrComponent)s "<a href="%(absoluteUrl)s">%(title)s</a>."<br>
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


</tr>''') % dict(adminFullname=admin.fullname, requesterAbsoluteUrl=requester.absolute_url, requesterFullname=requester.fullname, projectOrComponent=node.project_or_component, nodeAbsoluteUrl=node.absolute_url, title=node.title, contributorUrl=contributors_url, projectSettingsUrl=project_settings_url, rdmUrl=settings.RDM_URL, niiHomepageUrl=settings.NII_HOMEPAGE_URL, niiFormalnameEn=settings.NII_FORMAL_NAME_EN, niiFormalnameJa=settings.NII_FORMAL_NAME_JA, osfContactEmail=osf_contact_email)}
</%def>
