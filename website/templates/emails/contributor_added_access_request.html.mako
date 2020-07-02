<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${user.fullname}さん<br>
    <br>
    ${referrer_name + u'があなたのアクセス申請を承認しました' if referrer_name else u'あなたのアクセス申請が承認されました'}。GakuNin RDM上のプロジェクト(<a href="${node.absolute_url}">${node.title}</a>)のメンバーとして追加されました。<br>
    <br>
    このプロジェクト${u'から' if all_global_subscriptions_none else u'の'}通知メール${u'は送られてきません' if all_global_subscriptions_none else u'の送信が自動で始まります'}。メール通知設定はプロジェクトページあるいは<a href="${settings.DOMAIN + "settings/notifications/"}">ユーザ設定</a>から変更できます。<br>
    <br>
    よろしくお願いします。<br>
    <br>
    GakuNin RDMチーム<br>
    <br>
    GakuNin RDMの詳細については ${settings.RDM_URL} を、${settings.NII_FORMAL_NAME_JA}については ${settings.NII_HOMEPAGE_URL} をご覧ください。<br>
    <br>
    メールでのお問い合わせは ${osf_contact_email} までお願いいたします。<br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name + ' has approved your access request and added you' if referrer_name else 'Your access request has been approved, and you have been added'} as a contributor to the project "<a href="${node.absolute_url}">${node.title}</a>" on GRDM.<br>
    <br>
    You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '} notification emails for this project. To change your email notification preferences, visit your project or your <a href="${settings.DOMAIN + "settings/notifications/"}">user settings</a>.<br>
    <br>
    Sincerely,<br>
    <br>
    The GRDM Team<br>
    <br>
    Want more information? Visit ${settings.RDM_URL} to learn about GRDM, or ${settings.NII_HOMEPAGE_URL} for information about its supporting organization, the ${settings.NII_FORMAL_NAME_EN}.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>

</tr>
</%def>

