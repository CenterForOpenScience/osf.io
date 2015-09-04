<%inherit file="base.mako"/>
<%def name="title()">Developer Applications</%def>
<%def name="content()">
<h2 class="page-header">Settings</h2>

<div id="applicationListPage" class="row">
    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako" args="current_page='dev_apps'"/>
    </div>

    <div class="col-sm-9 col-md-7">

        <div id="appList" class="panel panel-default scripted" style="display:none;" data-bind="visible: true">
            <div class="panel-heading clearfix">
                <h3 class="panel-title" style="padding-bottom: 5px; padding-top: 5px;">Developer Applications</h3>
                <div class="pull-right">
                    <a data-bind="attr: {href: webCreateUrl}" role="button" class="btn btn-sm btn-default">New application</a>
                </div>
            </div>
            <div class="panel-body">

                <p>The OSF allows third-party web applications to connect to the OSF on behalf of other users via the OAuth 2.0 web application flow.</p>

                <p data-bind="visible: (appData().length == 0)">You have not registered any applications that can connect to the OSF on behalf of other users.</p>
                <div id="if-apps" data-bind="visible: (appData().length > 0)">
                    <p>You have registered the following applications that can connect to the OSF on behalf of other users:</p>

                    <table class="table table-condensed">
                        <thead>
                        <tr>
                            <th>Application</th>
                            <th>
                                <span class="pull-right">
                                    Deactivate
                                </span>
                            </th>
                        </tr>
                        </thead>
                        <tbody data-bind="foreach: sortedByName">
                            <tr>
                                <td>
                                    <a href="#" data-bind="attr: {href: webDetailUrl  }"><span data-bind="text: name"></span></a>
                                    <p>Client ID: <span class="text-muted" data-bind="text: clientId"></span></p>
                                </td>
                                <td>
                                    <a href="#" data-bind="click: $root.deleteApplication.bind($root)"><i class="fa fa-times text-danger pull-right"></i></a>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div> <!-- End panel body -->
        </div> <!-- End ViewModel section -->
    </div>

</div>
</%def>


<%def name="javascript_bottom()">

<script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.urls = {
        apiListUrl: ${ app_list_url | sjson, n },
        webCreateUrl: ${ web_url_for('oauth_application_register') | sjson, n }
    };
</script>
<script src=${"/static/public/js/profile-settings-applications-list-page.js" | webpack_asset}></script>
</%def>
