<%inherit file="base.mako"/>
<%def name="title()">mAP core API agreement</%def>

<%def name="content()">

<p/>

<div style="text-align: center">
<p>
学認RDMを利用するためにはmAP core(学認クラウドゲートウェイのグループ管理機能)とアカウントの同期を行う必要があります。
</p>

<p>
<button type="button" class="btn btn-primary" onclick="location.href='${mapcore_authcode_url}'">アカウント連携</button>
</p>

<p>
<a target="_blank" href="https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=17927724">
学認クラウドゲートウェイサービスについて
</a>
</p>
</div>

</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/my-projects.css">
    <link rel="stylesheet" href="/static/css/pages/dashboard-page.css">
</%def>
