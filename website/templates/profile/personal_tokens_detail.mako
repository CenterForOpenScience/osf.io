<%inherit file="base.mako"/>
<%def name="title()">Personal Token Detail</%def>
<%def name="content()">

    <h2 class="page-header">Settings</h2>


<div id="personalTokenDetailPage" class="row">
    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako"/>
    </div>

    <div class="col-sm-9 col-md-7" id="tokenDetail" style="display:none;" data-bind="visible: true">
        <div class="row">
            <div class="col-sm-12">
                <div class="breadcrumb"><i class="fa fa-angle-double-left"></i> <a data-bind="attr: {href: $root.webListUrl}">Return to list of registered tokens</a></div>
            </div>
        </div>


        <div data-bind="with: tokenData()">
            <div id="token-fields">
                <form novalidate class="form-inline" role="form" data-bind="submit: $root.submit.bind($root), validationOptions: {insertMessages: false, messagesOnModified: false}">
                    <div class="form-group">
                        <label>Token name: </label> <i class="fa fa-info-circle text-muted" data-bind="tooltip: {title: 'What this token is for.', placement: 'bottom'}"></i>
                        <input class="form-control" type="text" data-bind="value: name" required="required" placeholder="Required">
                        <p data-bind="validationMessage: name, visible: $root.showMessages()" class="text-danger"></p>
                    </div>

                    <div>
                        <label>Scopes: </label> <i class="fa fa-info-circle text-muted"
                       data-bind="tooltip: {title:'Scopes limit access for personal access tokens.',
                                            placement: 'bottom'}"></i>
                        <br/>
                        <div class="form-group" style="{margin-left: 5px}">

                            % for scope in scope_options:
                                <input type="checkbox" id="${scope[0]}" value="${scope[0]}" data-bind="checked: scopes">
                                <label for="${scope[0]}">${scope[0]} </label>
                                <i class="fa fa-info-circle text-muted" data-bind="tooltip: {title: ${scope[1] | sjson, n }, placement: 'bottom'}"></i>
                                <br>
                            % endfor
                         </div>
                        <p data-bind="validationMessage: scopes, visible: $root.showMessages()" class="text-danger"></p>
                    </div>

                    <div class="padded action-buttons">
                        <button type="reset" class="btn btn-default"
                                data-bind="click: $root.cancelChange.bind($root)">Cancel</button>
                        <button type="submit" class="btn btn-success"
                                data-bind="visible: $root.isCreateView()">Create</button>
                        <button type="button" class="btn btn-danger"
                                data-bind="visible: !$root.isCreateView(), click: $root.deleteToken.bind($root)">Delete</button>
                        <button type="submit" class="btn btn-success"
                                data-bind="visible: !$root.isCreateView()">Save</button>
                    </div>

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <p data-bind="html: $root.message, attr: {class: $root.messageClass}"></p>
                    </div>

                    <div id="token-keys" class="border-box text-left"
                         data-bind="visible: $root.showToken()">
                        <div class="bg-danger f-w-xl token-warning">This is the only time your token will be displayed.</div>
                        <label class="f-w-xl">Token ID</label>
                        <i class="fa fa-info-circle text-muted" data-bind="tooltip: {title:'ID used to authenticate with this token. This will be shown only once.',        placement: 'bottom'}"></i>
                        <span data-bind="text: token_id" id="token-id-text"></span>
                        <div>
                            <button type="button" class="btn btn-primary" data-bind="attr: {'data-clipboard-text': token_id}" id="copy-button"><i class="fa fa-copy"></i> Copy to clipboard</button>
                        </div>
                    </div>
                </form>

            </div>
        </div>
    </div>
</div>
</%def>

<%def name="javascript_bottom()">
<script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.urls = {
        webListUrl: ${ web_url_for('personal_access_token_list') | sjson, n },
        apiListUrl: ${ token_list_url | sjson, n },
        apiDetailUrl: ${ token_detail_url | sjson, n }
    };

    // Make sure to display tooltips correctly
    $(document).ready(function(){
        $('[data-toggle="tooltip"]').tooltip();
    });

</script>
<script src=${"/static/public/js/profile-settings-personal-tokens-detail-page.js" | webpack_asset}></script>
</%def>
