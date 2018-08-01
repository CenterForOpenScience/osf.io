<!-- Authorization -->
<div id='s3AddonScope' class='addon-settings addon-generic scripted'
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">

    <%include file="s3_credentials_modal.mako"/>

    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        <span data-bind="text: properName"></span>
        <small>
            <a href="#s3InputCredentials" data-toggle="modal" class="pull-right text-primary">Connect or Reauthorize Account</a>
        </small>
    </h4>

    <div class="addon-auth-table" id="${addon_short_name}-header" style="clear: both;">
        <!-- ko foreach: accounts -->
        
        <div class="account_heading" style="display: flex; flex-direction: row; align-items: baseline; flex-wrap: wrap; justify-content: flex-end; margin-left: 15px;">
            <div class="account_actions" style="display: flex; flex: 0 1 auto; flex-wrap: wrap; justify-content: flex-end">
                <a data-bind="click: $root.askDisconnect.bind($root)" class="text-danger pull-right default-authorized-by" style="padding-left: 5px; flex: 0 0 auto; text-align: right">Disconnect Account</a>
            </div>
        </div>

        <div class="m-h-lg" style="clear: both">

            <table class="table table-hover">
                <thead>
                    <tr class="user-settings-addon-auth">
                        <th class="text-muted default-authorized-by">
                            <!-- ko if: name -->
                                <div class="text-muted default-authorized-by">
                                    Authorized by <em data-bind="text: name"></em>
                                </div>
                            <!-- /ko -->
                            <!-- ko if: host -->
                                <div class="text-muted" style="flex: 1 0 auto">
                                    Account URL <em data-bind="text: host"></em>
                                </div>
                            <!-- /ko -->
                        </th>
                    </tr>
                </thead>
                <!-- ko if: connectedNodes().length > 0 -->
                <tbody data-bind="foreach: connectedNodes()">
                    <tr>
                        <td class="authorized-nodes">
                            <!-- ko if: title --><a data-bind="attr: {href: urls.view}, text: title"></a><!-- /ko -->
                            <!-- ko if: !title --><em>Private project</em><!-- /ko -->
                        </td>
                        <td>
                            <a data-bind="click: $parent.deauthorizeNode.bind($parent)">
                                <i class="fa fa-times text-danger pull-right" title="Disconnect Project"></i>
                            </a>
                        </td>
                    </tr>
                </tbody>
                <!-- /ko -->
                <!-- ko if:connectedNodes().length == 0 -->
                <tbody>
                    <tr>
                        <td>
                            There are no projects using this account.
                        </td>
                        <td></td>
                    </tr>
                </tbody>
                <!-- /ko -->
            </table>
        </div>
        <!-- /ko -->
    </div>
</div>
