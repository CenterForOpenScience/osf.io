<!-- Authorization -->
<div class="addon-oauth"
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}" aria-label="${addon_full_name} icon" alt="${addon_full_name} icon"">
      <span data-bind="text:properName"></span>
      <small>
        <a data-bind="click: connectAccount" class="pull-right text-primary">Connect or Reauthorize Account</a>
      </small>
    </h4>
    <div class="addon-auth-table" id="${addon_short_name}-header">
        <!-- ko foreach: accounts -->
        <a data-bind="click: $root.askDisconnect.bind($root)" class="text-danger pull-right default-authorized-by">Disconnect Account</a>

        <div class="m-h-lg">
            <table class="table table-hover">
                <thead>
                    <tr class="user-settings-addon-auth">
                        <th class="default-authorized-by">Authorized by <em><span data-bind="text: name"></span></em></th><th></th>
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
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>
