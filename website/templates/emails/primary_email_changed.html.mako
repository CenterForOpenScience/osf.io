<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    こんにちは、${user.fullname}さん<br>
    <br>
    あなたのGakuNin RDMアカウントのプライマリーメールアドレスは${new_address}に変更されました。<br>
    <br>
    このアクションをリクエストしていない場合は、 ${osf_contact_email} までお知らせください。<br>
    <br>
    どうぞよろしくお願いいたします。<br>
    <br>
    GakuNin RDM ボット<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    The primary email address for your GRDM account has been changed to ${new_address}.<br>
    <br>
    If you did not request this action, let us know at ${osf_contact_email}.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The GRDM Robot<br>

</tr>
</%def>
