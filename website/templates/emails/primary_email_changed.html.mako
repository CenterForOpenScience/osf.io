<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    こんにちは、${user.fullname}さん<br>
    <br>
    あなたのGRDMアカウントのプライマリーメールアドレスは${new_address}に変更されました。<br>
    <br>
    このアクションをリクエストしていない場合は、 rdm_support@nii.ac.jp までお知らせください。<br>
    <br>
    どうぞよろしくお願いいたします。<br>
    <br>
    GRDMロボット<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    The primary email address for your GRDM account has been changed to ${new_address}.<br>
    <br>
    If you did not request this action, let us know at rdm_support@nii.ac.jp.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The GRDM Robot<br>

</tr>
</%def>
