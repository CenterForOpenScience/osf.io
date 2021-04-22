<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${user.fullname}さん<br>
    <br>
    ${referrer_name + u'があなたを' if referrer_name else u'あなたは'}GakuNin RDM上のプロジェクト(${node.title})のメンバーとして追加${u'しました' if referrer_name else u'されました'}: <a href="${node.absolute_url}">${node.absolute_url}</a><br>
    <br>
    このプロジェクト${u'から' if all_global_subscriptions_none else u'の'}通知メール${u'は送られてきません' if all_global_subscriptions_none else u'の送信が自動で始まります'}。メール通知設定はプロジェクトページまたはユーザー設定から変更できます： <a href="${settings.DOMAIN + "settings/notifications/"}">${settings.DOMAIN + "settings/notifications/"}</a><br>
    <br>
    手違いであなたが「${node.title}」と関連付けられている場合、プロジェクトのメンバーページに行ってご自分をメンバーから外してください。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
    GakuNin RDM ボット<br>
    <br>
    GakuNin RDMの詳細については <a href="${settings.RDM_URL}">${settings.RDM_URL}</a> を、${settings.NII_FORMAL_NAME_JA}については <a href="${settings.NII_HOMEPAGE_URL}">${settings.NII_HOMEPAGE_URL}</a> をご覧ください。<br>
    <br>
    メールでのお問い合わせは <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>までお願いいたします。<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the project "${node.title}" on the GakuNin RDM: <a href="${node.absolute_url}">${node.absolute_url}</a><br>
    <br>
    You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this project. To change your email notification preferences, visit your project or your user settings: <a href="${settings.DOMAIN + "settings/notifications/"}">${settings.DOMAIN + "settings/notifications/"}</a><br>
    <br>
    If you are erroneously being associated with "${node.title}," then you may visit the project's "Contributors" page and remove yourself as a contributor.<br>
    <br>
    Sincerely,<br>
    <br>
    GakuNin RDM Robot<br>
    <br>
    Want more information? Visit <a href="${settings.RDM_URL}">${settings.RDM_URL}</a> to learn about the GakuNin RDM, or <a href="${settings.NII_HOMEPAGE_URL}">${settings.NII_HOMEPAGE_URL}</a> for information about its supporting organization, the ${settings.NII_FORMAL_NAME_EN}.<br>
    <br>
    Questions? Email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a><br>

</tr>
</%def>
