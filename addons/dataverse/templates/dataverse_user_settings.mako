<!-- Authorization -->
<div id='dataverseAddonScope' class='addon-settings addon-generic scripted'
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">

    <%include file="dataverse_credentials_modal.mako"/>

    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url} aria-label="Dataverse icon" alt="Dataverse icon">
        <span data-bind="text: properName"></span> <!-- TODO: Can we use mako addon_full_name as some other addons do? -->
        <small>
            <a href="#dataverseInputCredentials" data-toggle="modal" class="pull-right text-primary">Connect or Reauthorize Account</a>
        </small>
    </h4>

    <div class="addon-auth-table" id="${addon_short_name}-header">
        <!-- ko foreach: accounts -->
        <a data-bind="click: $root.askDisconnect.bind($root)" class="text-danger pull-right default-authorized-by">Disconnect Account</a>
        <div class="m-h-lg addon-auth-table" id="${addon_short_name}-header">
            <table class="table table-hover">
                <thead>
                    <tr class="user-settings-addon-auth">
                        <th class="default-authorized-by">Authorized on <a data-bind="attr: {href: dataverseUrl}"><em data-bind="text: dataverseHost"></em></a></th><th></th>
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
                                <i class="fa fa-times text-danger pull-right" title="Deauthorize Project"></i>
                            </a>
                        </td>
                    </tr>
                </tbody>
                <!-- /ko -->
            </table>
        </div>
        <!-- /ko -->
    </div>
</div>
