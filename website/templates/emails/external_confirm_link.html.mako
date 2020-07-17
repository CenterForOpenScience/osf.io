<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    こんにちは、${user.fullname}さん<br>
    <br>
    ${external_id_provider}アカウントをGakuNin RDMにリンクして頂いてありがとうございます。${external_id_provider}をあなたのGakuNin RDMプロフィールに追加します。<br>
    <br>
    リンクをクリックしてメールアドレスを認証してください：<br>
    <br>
    ${confirmation_url}<br>
    <br>
    GakuNin RDM チーム<br>


</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Thank you for linking your ${external_id_provider} account to the GakuNin RDM. We will add ${external_id_provider} to your GRDM profile.<br>
    <br>
    Please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    The GRDM Team<br>


</tr>
</%def>
