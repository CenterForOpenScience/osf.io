<div id="dataverseInputCredentials" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>${_("Connect a Dataverse Account")}</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">

                        <div class="col-sm-6">

                            <!-- Select Dataverse installation -->
                            <div class="form-group">
                                <label for="hostSelect">${_("Dataverse Repository")}</label>
                                <select class="form-control"
                                        id="hostSelect"
                                        data-bind="options: visibleHosts,
                                                   optionsCaption: '${_("Select a Dataverse repository")}',
                                                   value: selectedHost,
                                                   event: { change: selectionChanged }">
                                </select>
                            </div>

                            <!-- Custom input -->
                            <div data-bind="if: useCustomHost">
                                <div class="input-group">
                                    <div class="input-group-addon">https://</div>
                                    <input type="text" class="form-control" name="customHost" data-bind="value: customHost">
                                </div>
                                <div class="text-info" style="text-align: center">
                                    <em>${_("Only Dataverse repositories v4.0 or higher are supported.")}</em>
                                </div>
                            </div>

                        </div>

                        <div class="col-sm-6">

                            <!-- API Token Input-->
                            <div class="form-group" data-bind="if: showApiTokenInput">
                                <label for="apiToken">
                                    ${_("API Token")}
                                    <!-- Link to API token generation page -->
                                    <a data-bind="attr: {href: tokenUrl}"
                                       target="_blank" class="text-muted addon-external-link">
                                        ${_('(Get from Dataverse %(dataverseLink)s)') % dict(dataverseLink='<i class="fa fa-external-link-square"></i>') | n}
                                    </a>
                                </label>
                                <input class="form-control" name="apiToken" data-bind="value: apiToken"/>
                            </div>

                        </div>

                    </div><!-- end row -->

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <p data-bind="html: message, attr: {class: messageClass}"></p>
                    </div>

                </div><!-- end modal-body -->

                <div class="modal-footer">

                    <div data-bind="visible: authorizing" class="ball-pulse ball-scale-blue text-center">
                      <div></div>
                      <div></div>
                      <div></div>
                    </div>

                    <a href="#" class="btn btn-default" data-bind="click: clearModal" data-dismiss="modal">${_("Cancel")}</a>

                    <!-- Save Button -->
                    <button data-bind="click: sendAuth, css: {'disabled': authorizing}" class="btn btn-success">${_("Save")}</button>

                </div><!-- end modal-footer -->

            </form>

        </div><!-- end modal-content -->
    </div>
</div>
