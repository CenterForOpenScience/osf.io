<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    こんにちは、${fullname}さん<br>
    <br>
    あなたは${referrer.fullname}によって、GakuNin RDMのプロジェクト(${node.title})のメンバーとして追加されました。
% if login_by_eppn:
あなたのアカウントで確認する場合は、こちらをご覧ください：<br>
% else:
アカウントのパスワードを設定する場合は、こちらをご覧ください：<br>
% endif
    <br>
    ${claim_url}<br>
    <br>
% if login_by_eppn:
    継続すると、
% else:
    パスワードを設定すると、
% endif
    「${node.title}」に貢献したり、自分自身のプロジェクトを作成することができるようになります。 このプロジェクトの通知メールの送信が自動で始まります。メール通知設定はプロジェクトページまたはユーザー設定から変更できます： ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    「${node.title}」をプレビューするには、以下のリンクをクリックしてください：${node.absolute_url}<br>
    <br>
    「${node.title}」への参加登録を解除する場合は、以下のリンクをクリックしてください：${claim_url}&cancel=true<br>
    <br>
    (注：アカウントを確認するまで、表示することはできません)<br>
    <br>
    もしあなたが${fullname}ではない、あるいは手違いで「${node.title}」と関連付けられている場合は、${osf_contact_email}に件名「Claiming Error」で問題を報告するようメールしてください。<br>
    <br>
    よろしくお願いいたします。<br>
    <br>
    GakuNin RDM ボット<br>
    <br>
    GakuNin RDMの詳細については https://rdm.nii.ac.jp/ を、国立情報学研究所については https://nii.ac.jp/ をご覧ください。<br>
    <br>
    メールでのお問い合わせは ${osf_contact_email} までお願いいたします。<br>
    <br>
    Orthrosアカウントでプロジェクトに参加する場合、お使いのアカウントについて以下の遵守をお願いします。<br>
    <br>
    ・登録メールアドレスは機関ドメインを使用する（フリーメール非推奨）<br>
    ・プロフィールの所属欄を入力する<br>
    <br>
    Orthrosアカウントを持っていても、所属機関がGakuNin RDM未申請な場合、あるいは所属機関によってOrthrosによるGakuNin RDMの利用が認められていない場合はご利用いただけません。<br>
    導入についてはご所属の情報センター部門・研究推進部門・図書館等へご相談ください。<br>
    https://support.rdm.nii.ac.jp/about/ <br>
    利用資格のないユーザと判断できる場合は、GakuNin RDMの利用を制限する可能性がございます。<br>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${fullname},<br>
    <br>
    You have been added by ${referrer.fullname} as a contributor to the project "${node.title}" on the GakuNin RDM.
% if login_by_eppn:
To confirm for your account, visit:<br>
% else:
To set a password for your account, visit:<br>
% endif
    <br>
    ${claim_url}<br>
    <br>
% if login_by_eppn:
    Once you have continue,
% else:
    Once you have set a password,
% endif
    you will be able to make contributions to "${node.title}" and create your own projects. You will automatically be subscribed to notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    To preview "${node.title}" click the following link: ${node.absolute_url}<br>
    <br>
    To cancel register join "${node.title}" click the following link: ${claim_url}&cancel=true<br>
    <br>
    (NOTE: you will not be able to view it until you have confirmed your account)<br>
    <br>
    If you are not ${fullname} or you are erroneously being associated with "${node.title}" then email ${osf_contact_email} with the subject line "Claiming Error" to report the problem.<br>
    <br>
    Sincerely,<br>
    <br>
    GakuNin RDM Robot<br>
    <br>
    Want more information? Visit https://rdm.nii.ac.jp/ to learn about the GakuNin RDM, or https://nii.ac.jp/ for information about its supporting organization, the National Institute of Informatics.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>
    <br>
    If you are participating in a project with an Orthros account, please adhere to the following for your account<br>
    <br>
    ・Register an institutional domain email address  (free mail is not recommended)<br>
    ・Fill in the affiliation field of your profile.<br>
    <br>
    Even if you have an Orthros account, you will not be able to use GakuNin RDM if your institution has not applied for GakuNin RDM or if you are not authorized to use GakuNin RDM by Orthros.<br>
    Please consult with your Information Center, Research Promotion Division, Library, etc. regarding the introduction of GakuNin RDM.<br>
    https://support.rdm.nii.ac.jp/en/about/ <br>
    If you are determined to be an unqualified user, your use of GakuNin RDM may be restricted.<br>
</tr>
</%def>
