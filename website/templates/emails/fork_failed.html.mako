<%inherit file="notify_base.mako" />


<%def name="content()">
<% from website import settings %>
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">
        エラーが発生し、GakuNin RDM上で<b>${title}</b>のフォーク作成に失敗しました。ログインしてもう一度試してください。問題が解決しない場合は、rdm_support@nii.ac.jpまで問い合わせてください。.
    </h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">
        An error has occurred, and the fork of <b>${title}</b> on the GakuNin RDM was not successfully created. Please log in and try this action again. If the problem persists, please email rdm_support@nii.ac.jp.
    </h3>
  </td>
</tr>
</%def>
