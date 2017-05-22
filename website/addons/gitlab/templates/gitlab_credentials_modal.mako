<div id="gitlabInputCredentials" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header"><h3>Connect a GitLab Account</h3></div>
            <form>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-sm-6">
                            <!-- Select GitLab installation -->
                            <div class="form-group">
                                <label for="hostSelect">GitLab Repository</label>
                                <select class="form-control" id="hostSelect"
                                        data-bind="options: visibleHosts,
                                                   optionsCaption: 'Select a GitLab repository',
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
                                    <em>Only GitLab repositories v4.0 or higher are supported.</em>
                                </div>
                            </div>

                        </div>

                        <div class="col-sm-6">
                            <!-- Personal Access Token Input-->
                            <div class="form-group" data-bind="if: showApiTokenInput">
                                <label for="clientId">
                                    Personal Access Token
                                    <!-- Link to API token generation page -->
                                    <a data-bind="attr: {href: tokenUrl}"
                                       target="_blank" class="text-muted addon-external-link">
                                        (Get from GitLab <i class="fa fa-external-link-square"></i>)
                                    </a>
                                </label>
                                <input class="form-control" name="clientId" data-bind="value: clientId"/>
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
                    <button data-bind="click: sendAuth" class="btn btn-success">Save</button>

                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal-content -->
    </div>
</div>
