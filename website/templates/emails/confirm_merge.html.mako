<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${merge_target.fullname}さん<br>
    <br>
    This email is to notify you that ${user.username} has initiated an account merge with your account on the GakuNin RDM (GRDM). This merge will move all of the projects and components associated with ${email} and with ${user.username} into one account. All projects and components will be displayed under ${user.username}.本メールは、GakuNin RDM (GRDM)上で${user.username}があなたのアカウントとのアカウントマージを開始したことを通知するメールです。アカウントマージによって、全てのプロジェクトおよび${email}と${user.username}に関連するコンポーネントが全て1つのアカウントに移動されます。全てのプロジェクトとコンポーネントは${user.username}名義で表示されます。<br>
    <br>
    アカウントへのログインには${user.username}と${email}の両方を使います。しかし、${email}はユーザー検索時には表示されません。<br>
    <br>
    アカウントマージを実行するには次のリンクをクリックしてください：${confirmation_url}<br>
    <br>
    アカウントマージを希望しないのであれば、これ以上の操作は不要です。本メールについて質問がある場合は、${osf_support_email}までお問い合わせください。<br>
    <br>
    ${settings.NII_FORMAL_NAME_JA}<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${merge_target.fullname},<br>
    <br>
    This email is to notify you that ${user.username} has initiated an account merge with your account on the GakuNin RDM (GRDM). This merge will move all of the projects and components associated with ${email} and with ${user.username} into one account. All projects and components will be displayed under ${user.username}.<br>
    <br>
    Both ${user.username} and ${email} can be used to log into the account. However, ${email} will no longer show up in user search.<br>
    <br>
    This action is irreversible. To confirm this account merge, click this link: ${confirmation_url}.<br>
    <br>
    If you do not wish to merge these accounts, no action is required on your part. If you have any questions about this email, please direct them to ${osf_support_email}.<br>
    <br>
    ${settings.NII_FORMAL_NAME_EN}<br>

</tr>
</%def>
