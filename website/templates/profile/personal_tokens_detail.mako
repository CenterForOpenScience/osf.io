<%inherit file="base.mako"/>
<%def name="title()">Personal Token Detail</%def>
<%def name="content()">

    <h2 class="page-header">Personal Token Detail</h2>


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
            <div id="token-keys" class="border-box text-right"
                 data-bind="visible: !$root.isCreateView()">
                <p><strong>Token Name</strong>
                   <i class="fa fa-info-circle text-muted" data-bind="tooltip: {title: 'What this token is for.',
                                                                      placement: 'bottom'}"></i>
                </p>
                <p><span class="text-muted" data-bind="text: name"></span></p>

                <p><strong class="m-b-sm">Scopes</strong>
                    <i class="fa fa-info-circle text-muted"
                       data-bind="tooltip: {title:'The client secret is known only to you and the OSF. Do not display or expose this information.',
                                            placement: 'bottom'}"></i>
                </p>
                <p>
                   <span class="text-muted"
                         data-bind="html:  $root.showSecret() ? clientSecret : '&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;'"></span>
                    <a class="btn btn-default btn-xs m-l-sm " data-bind="click: $root.toggleDisplay.bind($root)">
                        <span data-bind="visible: $root.showSecret()"><i class="fa fa-eye-slash"></i> Hide</span>
                        <span data-bind="visible: !$root.showSecret()"><i class="fa fa-eye"></i> Show</span>
                    </a>
                </p>
                <p data-bind="visible: !$root.isCreateView()">
                    <a data-bind="click: $root.deleteToken.bind($root)" class="text-danger">Deactivate token</a>
                </p>
            </div>
            <div id="token-fields">
                <form novalidate role="form" data-bind="submit: $root.submit.bind($root), validationOptions: {insertMessages: false, messagesOnModified: false}">
                    <div class="form-group">
                        <label>Token name</label><i class="fa fa-info-circle text-muted" data-bind="tooltip: {title: 'What this token is for.', placement: 'bottom'}"></i>
                        <input class="form-control" type="text" data-bind="value: name" required="required" placeholder="Required">
                        <p data-bind="validationMessage: name, visible: $root.showMessages()" class="text-danger"></p>
                    </div>

                    <div class="form-group">
                        <label>Scopes</label> <i class="fa fa-info-circle text-muted"
                       data-bind="tooltip: {title:'Scopes limit access for personal access tokens.',
                                            placement: 'bottom'}"></i>
                        <input type="checkbox" class="form-control" data-bind="value: fullRead">Full Read</input>
                        <input type="checkbox" class="form-control" data-bind="value: fullWrite">Full Write</input>
                        <p data-bind="validationMessage: callbackUrl, visible: $root.showMessages()" class="text-danger"></p>
                    </div>

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <p data-bind="html: $root.message, attr.class: $root.messageClass"></p>
                    </div>

                    <div class="padded">
                        <button type="reset" class="btn btn-default"
                                data-bind="click: $root.cancelChange.bind($root)">Cancel</button>
                        <button type="submit" class="btn btn-success"
                                data-bind="visible: $root.isCreateView()">Create</button>
                        <button type="submit" class="btn btn-success"
                                data-bind="visible: !$root.isCreateView()">Save</button>
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
        webListUrl: ${ web_url_for('personal_token_list') | sjson, n },
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
