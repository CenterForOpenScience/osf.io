<!-- Authorization -->
<div class="addon-oauth"
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">  
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
      <span data-bind="text:properName"></span>
      <small>
        <a data-bind="click: connectAccount" class="pull-right text-primary">Connect Account</a>
      </small>
    </h4>
    <!-- ko foreach: accounts -->
    <table class="table">
        <thead>
            <tr class="user-settings-addon-auth">
                <th class="text-muted default-authorized-by">Authorized by <em><a data-bind="attr.href: profileUrl, text: name"></a></em></th>
                <th><a data-bind="click: $root.askDisconnect" class="text-danger pull-right default-authorized-by">Disconnect Account</a></th>
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
    <!-- /ko -->
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>
