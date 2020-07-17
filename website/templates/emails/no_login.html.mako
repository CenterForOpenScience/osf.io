## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        こんにちは、${fullname}さん
        <br><br>
        お客様がGakuNin RDM（GRDM）を前回使用してから、長い時間が経過しています。当サービスでは、常に各機能を追加し改善していますので、お客様にお知らせするのに良い機会だと考え、ご連絡いたしました。
        ほとんどの研究者の方々は、ファイルや記録を管理するため、プロジェクトを作成しGakuNin RDMのご利用を開始しています。プロジェクトは、お客様の研究を管理するのに役立つ、優れた機能を搭載しています。
        <br>
        <ul>
            <li>ウィキを使用して、共同研究者とコンテンツをライブエディットできます</li>
            <li>DropboxやGoogle Driveなどの第三者サービスに接続できます</li>
        </ul>
        開始するには、ダッシュボードに移動し、「プロジェクト作成」をクリックします。
        プロジェクトを開始するのにサポートが必要でしょうか？<a href="https://meatwiki.nii.ac.jp/confluence/display/gakuninrdmusers">GakuNin RDMのユーザサポート</a>をご確認ください。
        <br><br>
        よろしくお願いいたします。
        <br>
        NII サポートチーム

    </div>
    <div style="margin: 40px;">
        <br>
        Hello ${fullname},
        <br><br>
        We’ve noticed it’s been a while since you used the GakuNin RDM (GRDM). We are constantly adding and improving features, so we thought it might be time to check in with you.
        Most researchers begin using the GakuNin RDM by creating a project to organize their files and notes. Projects are equipped with powerful features to help you manage your research:
        <br>
        <ul>
            <li>You can keep your work private, or make it public and share it with others</li>
            <li>You can use the wiki to live-edit content with your collaborators</li>
            <li>You can connect to third-party services like Dropbox or Google Drive</li>
        </ul>
        To get started now, visit your dashboard and click on “Create a project.”
        Need help getting started with a project? Check out the <a href="https://openscience.zendesk.com/hc/en-us?utm_source=notification&utm_medium=email&utm_campaign=no_login">GakuNin RDM Help Guides</a> or one of our recent <a href="https://www.youtube.com/channel/UCGPlVf8FsQ23BehDLFrQa-g">GakuNin RDM 101 webinars</a>.
        <br><br>
        Sincerely,
        <br>
        NII Support Team

    </div>
</%def>
<%def name="footer()">
    <br>
    <a href="${osf_url}">GakuNin RDM</a>は<a href="https://nii.ac.jp/">国立情報学研究所</a>が提供するオープンソースサービスです。
    <br>
    The <a href="${osf_url}">GakuNin RDM</a> is provided as a free, open source service from the <a href="https://nii.ac.jp/">National Institute of Informatics</a>.
</%def>
