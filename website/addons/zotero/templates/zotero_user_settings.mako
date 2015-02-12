<!-- Authorization -->
<div id="zoteroUserSettings">
    <h4 class="addon-title">Zotero</h4>
    <table class="table">
        <tbody data-bind="foreach: accounts">
            <tr>
                <td data-bind="text: display_name"></td>
                <td data-bind="text: id"></td>
                <td><a data-bind="click: $root.askDisconnect" class="btn btn-danger">Remove</a></td>
            </tr>
        </tbody>
    </table>
    <a data-bind="click: connectAccount" class="btn btn-primary">Connect an account</a>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />