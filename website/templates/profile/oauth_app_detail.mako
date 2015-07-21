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

<h2 class="page-header">OAuth Application Settings</h2>

<div id="applicationDetailPage" class="row">
    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako"/>
    </div>

    <div class="col-sm-9 col-md-7">
        <div id="appDetail" data-bind="with: appData()">
            <div id="app-keys" class="border-box text-right text-muted"
                 data-bind="visible: !$root.isCreateView()">
                <p><span><strong>Client ID</strong>:</span> <br><span data-bind="text: clientId"></span></p>
                <p><span><strong>Client secret</strong>:</span> <br><span data-bind="text: clientSecret"></span></p>
            </div>
            <div id="app-fields">
                <!-- TODO: Add revoke/ reset buttons -->
                <form role="form" data-bind="validationOptions: {insertMessages: false, messagesOnModified: false}">
                    <div class="form-group">
                        <label>Application name</label>
                        <input class="form-control" type="text" data-bind="value: name" placeholder="Required">
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: name"></p>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Project homepage URL</label>
                        <input class="form-control" type="text" data-bind="value: homeUrl" placeholder="Required">
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: homeUrl"></p>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Application description</label>
                        <textarea class="form-control" placeholder="Application description is optional" data-bind="value: description"></textarea>
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: description"></p>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Authorization callback URL</label>
                        <input type="text" class="form-control" data-bind="value: callbackUrl" placeholder="Required">
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: callbackUrl"></p>
                        </div>
                    </div>

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <p data-bind="html: $root.message, attr.class: $root.messageClass"></p>
                    </div>

                    <div class="padded">
                        <button type="reset" class="btn btn-default" data-bind="click: $root.cancelChange">Cancel</button>
                        <button type="submit" class="btn btn-primary"
                                data-bind="visible: $root.isCreateView(), click: $root.createApplication">Create</button>

                        <button type="submit" class="btn btn-primary"
                                data-bind="visible: !$root.isCreateView(), click: $root.updateApplication">Save</button>
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
</script>
<script src=${"/static/public/js/profile-settings-applications-detail-page.js" | webpack_asset}></script>
</%def>
