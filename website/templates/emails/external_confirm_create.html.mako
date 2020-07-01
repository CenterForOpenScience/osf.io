<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    こんにちは、${user.fullname}さん<br>
    <br>
    ${external_id_provider}を使ってGakuNin RDMアカウントを登録して頂いてありがとうございます。あなたのGakuNin RDMのプロフィールに${external_id_provider}を追加します。<br>
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
    Thank you for registering with ${external_id_provider} for an account on the GakuNin RDM. We will add ${external_id_provider} to your GRDM profile.<br>
    <br>
    Please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    The GRDM Team<br>


</tr>
</%def>
