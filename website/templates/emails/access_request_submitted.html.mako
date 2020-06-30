<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${admin.fullname}さん<br>
    <br>
    <a href="${requester.absolute_url}">${requester.fullname}</a>から、あなたの${u'プロジェクト' if node.project_or_component == 'project' else u'コンポーネント'}(<a href="${node.absolute_url}">${node.title}</a>)へのアクセス申請がありました。<br>
    <br>
    申請をレビューするには<a href="${contributors_url}">こちら</a>をクリックしてください。アクセスの許可/拒否および権限設定ができます。<br>
    <br>
    あなたのプロジェクトで「アクセス申請」の機能が有効になっているために申請が送られています。共同作業を希望する人がいれば、この機能を使ってあなたのプロジェクトに参加させることができます。機能を無効化するには<a href="${project_settings_url}">こちら</a>をクリックしてください。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
    GakuNin RDMチーム<br>
    <br>
    GakuNin RDMの詳細については ${rdm_url} を、 ${nii_formal_name_ja} については ${nii_homepage_url} をご覧ください。<br>
    <br>
    メールでのお問い合わせは ${osf_contact_email} までお願いいたします。<br>


</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${admin.fullname},<br>
    <br>
    <a href="${requester.absolute_url}">${requester.fullname}</a> has requested access to your ${node.project_or_component} "<a href="${node.absolute_url}">${node.title}</a>."<br>
    <br>
    To review the request, click <a href="${contributors_url}">here</a> to allow or deny access and configure permissions.<br>
    <br>
    This request is being sent to you because your project has the 'Request Access' feature enabled. This allows potential collaborators to request to be added to your project. To disable this feature, click <a href="${project_settings_url}">here</a>.<br>
    <br>
    Sincerely,<br>
    <br>
    The GRDM Team<br>
    <br>
    Want more information? Visit https://rdm.nii.ac.jp/ to learn about GRDM, or https://www.nii.ac.jp/ for information about its supporting organization, the ${nii_formal_name_en}.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>


</tr>
</%def>
