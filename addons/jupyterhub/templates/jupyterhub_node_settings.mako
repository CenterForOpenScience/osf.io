<div id="jupyterhubScope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings">
        <div class="row">
            <div class="col-md-12">
              <span>
                <a href="#jupyterServiceDialog" data-toggle="modal"
                   class="btn btn-primary">
                  <i class="fa fa-plus" aria-hidden="true"></i> New
                </a>
              </span>
              <div class="pull-right">
                <button class="btn btn-success" data-bind="enable: dirtyCount, click: submit">
                  Save
                </button>
              </div>
            </div>
            <!-- end col -->
        </div>
        <!-- end row -->
        <div class="row">
            <div class="col-md-12">
              <!-- ko if: services().length > 0 -->
              <table class="table table-striped table-sm" style="margin: 0.5em;">
                <thead>
                  <tr>
                    <th>Service Name</th>
                    <th>Base URL</th>
                  </tr>
                </thead>
                <tbody data-bind="foreach: services">
                  <tr>
                    <th scope="row" data-bind="text: data.name"></th>
                    <td>
                      <a data-bind="attr: {href: data.base_url}, text: data.base_url"></a>
                      <div class="pull-right">
                        <button data-bind="click: $parent.editService"
                                class="btn" style="background-color:transparent">
                          <i class="fa fa-pencil-square-o" aria-hidden="true"></i>
                        </button>
                        <button data-bind="click: $parent.removeService"
                                class="btn" style="background-color:transparent">
                          <i class="fa fa-times" aria-hidden="true"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
              <!-- /ko -->
              <!-- ko if: services().length == 0 -->
                <div style="margin: 1em;">No JupyterHubs</div>
              <!-- /ko -->
            </div>
            <!-- end col -->
        </div>
        <!-- end row -->
    </div>

    <div id="jupyterServiceDialog" class="modal fade">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">

                <div class="modal-header">
                    <h3>Link JupyterHub</h3>
                </div>

                <form>
                    <div class="modal-body">

                        <div class="row">
                            <div class="col-sm-3"></div>

                            <div class="col-sm-6">
                                <div class="form-group">
                                    <label for="jupyterService">Service Name</label>
                                    <input class="form-control" data-bind="value: serviceName" id="service_name" name="service_name" ${'disabled' if disabled else ''} />
                                </div>
                                <div class="form-group">
                                    <label for="jupyterService">Service Base URL</label>
                                    <input class="form-control" data-bind="value: serviceBaseUrl" id="service_base_url" name="service_base_url" ${'disabled' if disabled else ''} />
                                </div>
                            </div>
                        </div><!-- end row -->

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr: {class: messageClass}"></p>
                        </div>

                    </div><!-- end modal-body -->

                    <div class="modal-footer">

                        <a href="#" class="btn btn-default" data-bind="click: clearModal" data-dismiss="modal">Cancel</a>

                        <!-- Save Button -->
                        <button data-bind="click: submitService" class="btn btn-success">OK</button>

                    </div><!-- end modal-footer -->

                </form>

            </div><!-- end modal-content -->
        </div>
    </div>
</div>
