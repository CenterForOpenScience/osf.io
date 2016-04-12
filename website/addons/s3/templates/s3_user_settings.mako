<!-- Authorization -->
<div id='s3AddonScope' class='addon-settings addon-generic scripted'
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">

    <%include file="s3_credentials_modal.mako"/>

    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        {{ properName }}
        <small>
            <a href="#s3InputCredentials" data-toggle="modal" class="pull-right text-primary">Connect Account</a>
        </small>
    </h4>

    <div class="addon-auth-table" id="${addon_short_name}-header">
        <!-- ko foreach: accounts -->
        <a data-bind="click: $root.askDisconnect" class="text-danger pull-right default-authorized-by">Disconnect Account</a>

        <div class="m-h-lg">
            <table class="table table-hover">
                <thead>
                    <tr class="user-settings-addon-auth">
                        <th class="text-muted default-authorized-by">Authorized by <em><span data-bind="text: name"></span></em></th>
                    </tr>
                </thead>
                <!-- ko if: connectedNodes().length > 0 -->
                <tbody data-bind="foreach: connectedNodes()">
                    <tr>
                        <td class="authorized-nodes">
                            <!-- ko if: title --><a data-bind="attr.href: urls.view, text: title"></a><!-- /ko -->
                            <!-- ko if: !title --><em>Private project</em><!-- /ko -->
                        </td>
                        <td>
                            <a data-bind="click: $parent.deauthorizeNode">
                                <i class="fa fa-times text-danger pull-right" title="disconnect Project"></i>
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
