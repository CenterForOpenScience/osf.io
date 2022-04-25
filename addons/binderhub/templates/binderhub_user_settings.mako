<!-- Authorization -->
<div id='${addon_short_name}Scope' class='addon-settings addon-generic scripted'
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">

    <!-- Add hosts modal -->
    <%include file="hosts_modal.mako"/>

    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        <span data-bind="text: properName"></span>
        <!-- ko if: !loading() -->
        <small>
            <a href="#binderhubInputHost" data-toggle="modal" class="pull-right text-primary">${_("Add BinderHub")}</a>
        </small>
        <!-- /ko -->
    </h4>

    <div class="addon-auth-table" id="${addon_short_name}-header">
        <!-- ko if: loading() -->
        <div class="m-h-lg">
            ${_('Loading...')}
        </div>
        <!-- /ko -->

        <!-- ko if: binderhubs().length > 0 -->
        <div class="m-h-lg">
            <table class="table table-hover">
                <thead>
                    <tr class="user-settings-addon-auth">
                        <th class="text-muted default-authorized-by">${_('BinderHub URL') | n}</th>
                    </tr>
                </thead>
                <tbody data-bind="foreach: binderhubs()">
                    <tr>
                        <td class="authorized-nodes">
                            <a data-bind="attr: {href: binderhub_url}, text: binderhub_url"></a>
                        </td>
                        <td>
                            <a data-bind="click: $parent.removeHost.bind($parent)">
                                <i class="fa fa-times text-danger pull-right" title="${_('disconnect Project')}"></i>
                            </a>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <!-- /ko -->
    </div>
</div>
