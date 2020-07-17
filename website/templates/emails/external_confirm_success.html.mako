<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    こんにちは、${user.fullname}さん<br>
    <br>
    おめでとうございます！ ${external_id_provider}アカウントとGakuNin RDM(GRDM)のリンクに成功しました。<br>
    <br>
    GakuNin RDM チーム<br>


</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Congratulations! You have successfully linked your ${external_id_provider} account to the GakuNin RDM (GRDM).<br>
    <br>
    The GRDM Team<br>


</tr>
</%def>
