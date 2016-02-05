<%inherit file="base.mako"/>
<%def name="title()">Personal Access Tokens</%def>
<%def name="content()">
<h2 class="page-header">Settings</h2>

<div id="personalTokenListPage" class="row">
    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako" args="current_page='personal_tokens'"/>
    </div>

    <div class="col-sm-9 col-md-7">

        <div id="tokensList" class="panel panel-default scripted" style="display:none;" data-bind="visible: true">
            <div class="panel-heading clearfix">
                <h3 class="panel-title" style="padding-bottom: 5px; padding-top: 5px;">Personal Access Tokens</h3>
                <div class="pull-right">
                    <a data-bind="attr: {href: webCreateUrl}" role="button" class="btn btn-sm btn-default">New token</a>
                </div>
            </div>
            <div class="panel-body">

                <p> Personal access tokens function like ordinary OAuth access tokens. They can be used to authenticate to the API.</p>

                <p data-bind="visible: (tokenData().length == 0)">You have not created any access tokens that can connect to the OSF.</p>
                <div id="if-tokens" data-bind="visible: (tokenData().length > 0)">
                    <p>You have generated the following personal access tokens:</p>

                    <table class="table table-condensed">
                        <thead>
                        <tr>
                            <th>Personal Access Tokens</th>
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
                                </td>
                                <td>
                                    <a href="#" data-bind="click: $root.deleteToken.bind($root)"><i class="fa fa-times text-danger pull-right"></i></a>
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
        apiListUrl: ${ token_list_url | sjson, n },
        webCreateUrl: ${ web_url_for('personal_access_token_register') | sjson, n }
    };
</script>
<script src=${"/static/public/js/profile-settings-personal-tokens-list-page.js" | webpack_asset}></script>
</%def>
