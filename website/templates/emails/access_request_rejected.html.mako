<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${requester.fullname}さん<br>
    <br>
    本メールは、${node.absolute_url}のプロジェクトへのアクセス申請が却下されたことを通知するものです。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
     GakuNin RDMチーム<br>
    <br>
    GakuNin RDMの詳細については ${settings.RDM_URL} を、 ${settings.NII_FORMAL_NAME_JA} については ${settings.NII_HOMEPAGE_URL} をご覧ください。<br>
    <br>
    メールでのお問い合わせは ${osf_contact_email} までお願いいたします。<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${requester.fullname},<br>
    <br>
    This email is to inform you that your request for access to the project at ${node.absolute_url} has been declined.<br>
    <br>
    Sincerely,<br>
    <br>
    The GRDM Team<br>
    <br>
    Want more information? Visit https://rdm.nii.ac.jp/ to learn about GRDM, or https://nii.ac.jp/ for information about its supporting organization, the ${settings.NII_FORMAL_NAME_EN}.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>

</tr>
</%def>

