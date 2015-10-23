<%inherit file="base.mako"/>
<%def name="title()">Application Detail</%def>
<%def name="content()">

    <h2 class="page-header">Application Detail</h2>


<div id="applicationDetailPage" class="row">
    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako"/>
    </div>

    <div class="col-sm-9 col-md-7" id="appDetail" style="display:none;" data-bind="visible: true">
        <div class="row">
            <div class="col-sm-12">
                <div class="breadcrumb"><i class="fa fa-angle-double-left"></i> <a data-bind="attr: {href: $root.webListUrl}">Return to list of registered applications</a></div>
            </div>
        </div>


        <div data-bind="with: appData()">
            <div id="app-keys" class="border-box text-right"
                 data-bind="visible: !$root.isCreateView()">
                <p><strong>Client ID</strong>
                   <i class="fa fa-info-circle text-muted" data-bind="tooltip: {title: 'The unique identifier for the application. May be seen publicly by others.',
                                                                      placement: 'bottom'}"></i>
                </p>
                <p><span class="text-muted" data-bind="text: clientId"></span></p>

                <p><strong class="m-b-sm">Client secret</strong>
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
                    <a class="btn btn-danger btn-xs m-l-sm" data-bind="click: $root.resetSecret.bind($root)">Reset Secret</a>
                    <i class="fa fa-info-circle text-muted"
                        data-bind="tooltip: {title:'Resetting the client secret will render your application unusable until it is updated with the new client secret, and all users must reauthorize access. Previously issued access tokens will no longer work.',
                                             placement: 'bottom'}"></i>
                </p>
                <p data-bind="visible: !$root.isCreateView()">
                    <a data-bind="click: $root.deleteApplication.bind($root)" class="text-danger">Deactivate application</a>
                </p>
            </div>
            <div id="app-fields">
                <form novalidate role="form" data-bind="submit: $root.submit.bind($root), validationOptions: {insertMessages: false, messagesOnModified: false}">
                    <div class="form-group">
                        <label>Application name</label>
                        <input class="form-control" type="text" data-bind="value: name" required="required" placeholder="Required">
                        <p data-bind="validationMessage: name, visible: $root.showMessages()" class="text-danger"></p>
                    </div>

                    <div class="form-group">
                        <label>Project homepage URL</label>
                        <input class="form-control" type="url" data-bind="value: homeUrl" required="required" placeholder="Required">
                        <p data-bind="validationMessage: homeUrl, visible: $root.showMessages()" class="text-danger"></p>
                    </div>

                    <div class="form-group">
                        <label>Application description</label>
                        <textarea class="form-control" placeholder="Optional" data-bind="value: description"></textarea>
                        <p data-bind="validationMessage: description, visible: $root.showMessages()" class="text-danger"></p>
                    </div>

                    <div class="form-group">
                        <label>Authorization callback URL</label>
                        <input type="url" class="form-control" data-bind="value: callbackUrl" required="required" placeholder="Required">
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
        </div> <!-- End appDetail section -->
    </div>
</div>
</%def>

<%def name="javascript_bottom()">
<script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.urls = {
        webListUrl: ${ web_url_for('oauth_application_list') | sjson, n },
        apiListUrl: ${ app_list_url | sjson, n },
        apiDetailUrl: ${ app_detail_url | sjson, n }
    };

    // Make sure to display tooltips correctly
    $(document).ready(function(){
        $('[data-toggle="tooltip"]').tooltip();
    });

</script>
<script src=${"/static/public/js/profile-settings-applications-detail-page.js" | webpack_asset}></script>
</%def>
