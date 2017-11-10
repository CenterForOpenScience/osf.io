<%inherit file="project/addon/widget.mako"/>

<div id="jupyterhubLinks" class="scripted">
  <!-- ko if: loading -->
  <div>Loading</div>
  <!-- /ko -->
  <!-- ko if: loadFailed -->
  <div class="text-danger">Error occurred</div>
  <!-- /ko -->
  <!-- ko if: loadCompleted -->
    <!-- ko if: availableServices().length > 0 -->
    <h5 style="padding: 0.2em;">Linked JupyterHubs</h5>
    <table class="table table-hover table-striped table-sm">
        <tbody data-bind="foreach: availableServices">
            <tr>
                <td>
                  <a data-bind="attr: {href: base_url}, text: name" target="_blank"></a>
                </td>
            </tr>
        </tbody>
    </table>
    <!-- /ko -->
    <!-- ko if: availableServices().length == 0 -->
    <div style="margin: 0.5em;">No Linked JupyterHubs</div>
    <!-- /ko -->
  <!-- /ko -->
  <div id="jupyterSelectionDialog" class="modal fade">
      <div class="modal-dialog modal-lg">
          <div class="modal-content">

              <div class="modal-header">
                  <h3>Select JupyterHub</h3>
              </div>

              <form>
                  <div class="modal-body">

                      <div class="row">
                          <div class="col-sm-6">
                            <ul data-bind="foreach: availableLinks">
                                <li>
                                    <a data-bind="attr: {href: url}, text: name" target="_blank"></a>
                                </li>
                            </ul>
                          </div>
                      </div><!-- end row -->

                  </div><!-- end modal-body -->

                  <div class="modal-footer">

                      <a href="#" class="btn btn-default" data-bind="click: clearModal" data-dismiss="modal">Close</a>

                  </div><!-- end modal-footer -->

              </form>

          </div><!-- end modal-content -->
      </div>
  </div>
</div>
