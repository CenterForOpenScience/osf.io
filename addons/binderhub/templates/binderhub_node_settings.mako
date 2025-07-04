<!-- for widget -->

<div id="${addon_short_name}Scope" class="scripted">

    <!-- Add new hosts modal -->
    <%include file="hosts_modal.mako"/>

    <!-- Add preset hosts modal -->
    <div id="binderhubInputPresetHost" class="modal fade">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">

                <div class="modal-header">
                    <h3>${_("Select a BinderHub client")}</h3>
                </div>

                <form>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-sm-3"></div>

                            <div class="col-sm-6">
                                <div class="form-group">
                                    <label for="binderhubAddon">${_("BinderHub URL")}</label>
                                    <select class="form-control"
                                            id="hostSelect"
                                            data-bind="options: presetHosts,
                                                       optionsCaption: '${_("Select a BinderHub")}',
                                                       optionsValue: 'binderhub_url',
                                                       optionsText: 'binderhub_name',
                                                       value: selectedHost">
                                    </select>
                                </div>
                            </div>
                        </div><!-- end row -->
                    </div><!-- end modal-body -->

                    <div class="modal-footer">
                        <a href="#" class="btn btn-default" data-bind="click: clearPresetModal" data-dismiss="modal">${_("Cancel")}</a>

                        <!-- Save Button -->
                        <button data-bind="click: addPresetHost, enable: selectedHost" class="btn btn-success">${_("Save")}</button>

                    </div><!-- end modal-footer -->

                </form>

            </div><!-- end modal-content -->
        </div>
    </div>


    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings">
        <div class="row">
            <div class="col-md-12">
                ${_("Default BinderHub URL:")}
                <a
                  data-bind="attr: {href: binderUrl}, text: binderUrl" target="_blank"
                  rel="noopener"
                ></a>
                <div class="addon-auth-table" id="${addon_short_name}-header">
                    <!-- ko if: loading() -->
                    <div>
                        ${_('Loading...')}
                    </div>
                    <!-- /ko -->

                    <div class="m-h-lg">
                        <table class="table table-hover">
                            <thead>
                                <tr class="user-settings-addon-auth">
                                    <th class="text-muted default-authorized-by">${_('BinderHub URL') | n}</th>
                                </tr>
                            </thead>
                            <tbody data-bind="foreach: availableBinderhubs()">
                                <tr>
                                    <td class="authorized-nodes">
                                        <a data-bind="attr: {href: binderhub_url}, text: binderhub_url"></a>
                                    </td>
                                    <td>
                                        <a data-bind="click: $parent.removeHost.bind($parent),
                                                      visible: 1 < $parent.availableBinderhubs().length">
                                            <i class="fa fa-times text-danger pull-right" title="${_('disconnect binderhub')}"></i>
                                        </a>
                                        <!-- ko if: $parent.binderUrl() != binderhub_url -->
                                        <a data-bind="click: $parent.updateDefaultUrl.bind($parent)">
                                            <i class="fa fa-square text-muted pull-right" title="${_('set to default')}"></i>
                                        </a>
                                        <!-- /ko -->
                                        <!-- ko if: $parent.binderUrl() == binderhub_url -->
                                        <i class="fa fa-check-square pull-right" title="${_('default')}"></i>
                                        <!-- /ko -->
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div>
                  <button href="#binderhubInputHost" data-toggle="modal" class="btn btn-success">
                      ${_("Add Host")}
                  </a>
                  <button href="#binderhubInputPresetHost" data-toggle="modal" class="btn btn-success" style="margin-left: 1em;">
                      ${_("Add Host from Account or GRDM")}
                  </a>
                </div>
            </div>
        </div>
        <!-- end row -->
    </div>
</div>
