<!-- Authorization -->
<div id="zoteroUserSettings">
    <h4 class="addon-title">Zotero</h4>
    <div data-bind="foreach: accounts">
        <div>
            <span>{{ name }}</span>
            <a data-bind="click: $root.askDisconnect" class="pull-right text-danger">Delete Access Token</a>
        </div>
    </div>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
    <a data-bind="click: connectAccount" class="btn btn-primary">Connect an account</a>
</div>
<%def name="submit_btn()">
</%def>
<%def name="on_submit()">
</%def>

<%include file="profile/addon_permissions.mako" />
