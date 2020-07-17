<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    ${user.fullname}様<br>
    <br>
    あなたのGakuNin RDMアカウントはスパムであるとフラグが立てられ停止されました。間違ってフラグを立てられた場合、${osf_support_email}までお問い合わせください。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
    GakuNin RDM チーム<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Dear ${user.fullname}, <br>
    <br>
    Your account on the GakuNin RDM has been flagged as spam and disabled. If this is in error, please email ${osf_support_email} for assistance.<br>
    <br>
    Regards,<br>
    <br>
    The GRDM Team<br>

</tr>
</%def>
