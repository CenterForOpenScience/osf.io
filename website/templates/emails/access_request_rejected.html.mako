<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${requester.fullname}さん<br>
    <br>
    本メールは、<a href="${node.absolute_url}">${node.absolute_url}</a>のプロジェクトへのアクセス申請が却下されたことを通知するものです。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
     GakuNin RDMチーム<br>
    <br>
    GakuNin RDMの詳細については <a href="${settings.RDM_URL}">${settings.RDM_URL}</a> を、${settings.NII_FORMAL_NAME_JA}については <a href="${settings.NII_HOMEPAGE_URL}">${settings.NII_HOMEPAGE_URL}</a> をご覧ください。<br>
    <br>
    メールでのお問い合わせは <a href="mailto:${osf_contact_email}">${osf_contact_email}</a> までお願いいたします。<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${requester.fullname},<br>
    <br>
    This email is to inform you that your request for access to the project at <a href="${node.absolute_url}">${node.absolute_url}</a> has been declined.<br>
    <br>
    Sincerely,<br>
    <br>
    The GRDM Team<br>
    <br>
    Want more information? Visit <a href="${settings.RDM_URL}">${settings.RDM_URL}</a> to learn about GRDM, or <a href="${settings.NII_HOMEPAGE_URL}">${settings.NII_HOMEPAGE_URL}</a> for information about its supporting organization, the ${settings.NII_FORMAL_NAME_EN}.<br>
    <br>
    Questions? Email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a><br>

</tr>
</%def>

