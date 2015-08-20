<%inherit file="base.mako"/>
<%def name="title()">Application Detail</%def>
<%def name="content()">
<style type="text/css">
    .border-box {
        padding: 15px 10px;
        border: solid #DDD;
        border-width: 1px 0;
        line-height: 1.1;
        display: block;
        margin-bottom: 1em;
    }
</style>

<h2 class="page-header">Application Detail</h2>


<div id="applicationDetailPage" class="row">
    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako"/>
    </div>

    <div class="col-sm-9 col-md-7">
        <div class="row">
            <div class="col-sm-12">
                <div class="breadcrumb"><i class="fa fa-angle-double-left"></i> <a href="${web_url_for('oauth_application_list')}">Return to list of registered applications</a></div>
            </div>
        </div>


        <div id="appDetail" data-bind="with: appData()">
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
                    <a class="btn btn-default btn-xs m-l-sm " data-bind="click: $root.toggleDisplay">
                        <span data-bind="visible: $root.showSecret()"><i class="fa fa-eye-slash"></i> Show</span>
                        <span data-bind="visible: !$root.showSecret()"><i class="fa fa-eye"></i> Hide</span>
                    </a>
                </p>
            </div>
            <div id="app-fields">
                ## TODO: Add revoke/ reset buttons
                <form role="form" data-bind="validationOptions: {insertMessages: false, messagesOnModified: false}">
                    <div class="form-group">
                        <label>Application name</label>
                        <input class="form-control" type="text" data-bind="value: name" placeholder="Required">

                            <p data-bind="validationMessage: name" class="text-danger"></p>
                    </div>

                    <div class="form-group">
                        <label>Project homepage URL</label>
                        <input class="form-control" type="text" data-bind="value: homeUrl" placeholder="Required">
                            <p data-bind="validationMessage: homeUrl" class="text-danger"></p>
                    </div>

                    <div class="form-group">
                        <label>Application description</label>
                        <textarea class="form-control" placeholder="Application description is optional" data-bind="value: description"></textarea>
                            <p data-bind="validationMessage: description" class="text-danger"></p>
                    </div>

                    <div class="form-group">
                        <label>Authorization callback URL</label>
                        <input type="text" class="form-control" data-bind="value: callbackUrl" placeholder="Required">
                            <p data-bind="validationMessage: callbackUrl" class="text-danger"></p>
                    </div>

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <p data-bind="html: $root.message, attr.class: $root.messageClass"></p>
                    </div>

                    <div class="padded">
                        <button type="reset" class="btn btn-default"
                                data-bind="click: $root.cancelChange">Cancel</button>
                        <button type="submit" class="btn btn-success"
                                data-bind="visible: $root.isCreateView(), click: $root.createApplication, enable: isValid()">Create</button>
                        <button data-bind="visible: !$root.isCreateView(), click: $root.deleteApplication" class="btn btn-danger">Deactivate</button>
                        <button type="submit" class="btn btn-success"
                                data-bind="visible: !$root.isCreateView(), click: $root.updateApplication, enable: (isValid() && $root.dirty())">Save</button>
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
