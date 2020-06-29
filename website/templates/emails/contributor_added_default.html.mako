<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${user.fullname}さん<br>
    <br>
    ${referrer_name + u'があなたを' if referrer_name else u'あなたは'}GakuNin RDM上のプロジェクト(${node.title})のメンバーとして追加${u'しました' if referrer_name else u'されました'}: ${node.absolute_url}<br>
    <br>
    このプロジェクト${u'から' if all_global_subscriptions_none else u'の'}通知メール${u'は送られてきません' if all_global_subscriptions_none else u'の送信が自動で始まります'}。メール通知設定はプロジェクトページまたはユーザー設定から変更できます： ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    手違いであなたが「${node.title}」と関連付けられている場合、プロジェクトのメンバーページに行ってご自分をメンバーから外してください。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
    GakuNin RDM ボット<br>
    <br>
    詳細をご希望ですか？GRDMについてはhttps://rdm.nii.ac.jp/を、国立情報科学研究所についてはhttps://www.nii.ac.jp/をご覧ください。<br>
    <br>
    メールでのお問い合わせは ${osf_contact_email} までお願いいたします。<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the project "${node.title}" on the GakuNin RDM: ${node.absolute_url}<br>
    <br>
    You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    If you are erroneously being associated with "${node.title}," then you may visit the project's "Contributors" page and remove yourself as a contributor.<br>
    <br>
    Sincerely,<br>
    <br>
    GakuNin RDM Robot<br>
    <br>
    Want more information? Visit https://rdm.nii.ac.jp/ to learn about the GakuNin RDM, or https://nii.ac.jp/ for information about its supporting organization, the National Institute of Informatics.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>

</tr>
</%def>
