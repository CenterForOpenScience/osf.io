<!-- Authorization -->
<div id='dataverseAddonScope' class='addon-settings scripted'
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">

    <%include file="dataverse_credentials_modal.mako"/>
    <a href="#dataverseInputCredentials" data-toggle="modal" class="pull-right text-primary">Connect an account</a>
    <h4 class="addon-title">{{ properName }}</h4>

    <!-- ko foreach: accounts -->
    <table class="table">
        <thead>
            <tr>
                <th>Authorized on <a href="{{ dataverseUrl }}"><em>{{ dataverseHost }}</em></a></th>
                <th><a data-bind="click: $root.askDisconnect" class="text-danger">Delete Access Token</a></th>
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
                        <i class="fa fa-times text-danger" title="Deauthorize Project"></i>
                    </a>
                </td>
            </tr>
        </tbody>
        <!-- /ko -->
    </table>
    <!-- /ko -->
</div>
