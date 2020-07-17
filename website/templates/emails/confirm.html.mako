<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    こんにちは、${user.fullname}さん<br>
    <br>
    このメールアドレスはGakuNin RDM上のアカウントに追加されました。<br>
    <br>
    リンクをクリックしてメールアドレスを認証してください：<br>
    <br>
    ${confirmation_url}<br>
    <br>
    どうぞよろしくお願いいたします。<br>
    <br>
    GakuNin RDM チーム<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    This email address has been added to an account on the GakuNin RDM.<br>
    <br>
    Please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    Sincerely yours,<br>
    <br>
    The GRDM Team<br>

</tr>
</%def>
