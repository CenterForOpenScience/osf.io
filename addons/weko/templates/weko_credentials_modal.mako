<div id="wekoInputCredentials" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>${_("Connect a JAIRO Cloud Account")}</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">

                        <div class="col-sm-6">

                            <!-- Select JAIRO Cloud installation -->
                            <div class="form-group">
                                <label for="hostSelect">${_("JAIRO Cloud Repository")}</label>
                                <select class="form-control"
                                        id="hostSelect"
                                        data-bind="options: repositories,
                                                   optionsText: 'name',
                                                   optionsCaption: '${_("Select a JAIRO Cloud repository")}',
                                                   value: selectedRepo,
                                                   event: { change: selectionChanged }">
                                </select>
                            </div>

                        </div>

                    </div><!-- end row -->

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <p data-bind="html: message, attr: {class: messageClass}"></p>
                    </div>

                </div><!-- end modal-body -->

                <div class="modal-footer">

                    <a href="#" class="btn btn-default" data-bind="click: clearModal" data-dismiss="modal">${_("Cancel")}</a>

                    <!-- Save Button -->
                    <button data-bind="click: connectOAuth" class="btn btn-success">${_("Connect")}</button>

                </div><!-- end modal-footer -->

            </form>

        </div><!-- end modal-content -->
    </div>
</div>
