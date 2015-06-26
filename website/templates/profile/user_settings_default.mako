<!-- Authorization -->
<div class="addon-oauth"
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">  
    <a data-bind="click: connectAccount" class="pull-right text-primary">Connect Account</a>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
      {{ properName }}
    </h4>
    <!-- ko foreach: accounts -->

    <table class="table">
        <thead>
            <tr>
                <th>Authorized by <a href="{{ profileUrl }}"><em>{{ name }}</em></a></th>
                <th><a data-bind="click: $root.askDisconnect" class="text-danger">Disconnect Account</a></th>
            </tr>
        </thead>
        <!-- ko if: connectedNodes().length > 0 -->
        <tbody data-bind="foreach: connectedNodes()">
            <tr>
                <td class="authorized-nodes">
                    <!-- ko if: title --><a href="{{ urls.view }}">{{ title }}</a><!-- /ko -->
                    <!-- ko if: !title --><em>Private project</em><!-- /ko -->
                </td>
                <td>
                    <a data-bind="click: $parent.deauthorizeNode">
                        <i class="fa fa-times text-danger" title="Disconnect Project"></i>
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
