<!-- Authorization -->
<div id="zoteroUserSettings">
    <h4 class="addon-title">Zotero</h4>
    <div data-bind="foreach: accounts">
        <div>
            <span data-bind="text: display_name"></span>
            <a data-bind="click: $root.askDisconnect" class="pull-right btn btn-danger">Remove</a>
        </div>
    </div>
    <br>
    <a data-bind="click: connectAccount" class="btn btn-primary">Connect an account</a>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />