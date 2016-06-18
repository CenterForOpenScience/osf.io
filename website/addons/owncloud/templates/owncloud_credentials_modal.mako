<div id="ownCloudCredentialsModal" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>Connect an ownCloud Account</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">

                        <div class="col-sm-6">

                            <div class="form-group">
                                <label for="hostSelect">ownCloud Instance</label>
                                <select class="form-control"
                                        id="hostSelect"
                                        data-bind="options: visibleHosts,
                                                   optionsCaption: 'Select an ownCloud Instance',
                                                   value: selectedHost,
                                                  ">
                                </select>
                            </div>

                            <!-- Custom input -->
                            <div data-bind="if: useCustomHost">
                                <div class="input-group">
                                    <div class="input-group-addon">https://</div>
                                    <input type="text" class="form-control" name="customHost" data-bind="value: customHost">
                                </div>
                                <div class="text-info" style="text-align: center">
                                    <em>only ownCloud instances supporting <a href="https://www.freedesktop.org/wiki/Specifications/open-collaboration-services-1.7/">
                                        OCS v1.7 are supported. <i class="fa fa-external-link-square"></i></a>
                                        </em>
                                </div>
                            </div>

                        </div>
                        <div class="col-sm-6">
                            <!-- API Token Input-->
                            <div class="form-group" data-bind="if: showCredentialInput">
                                <label for="username">
                                    Username
                                </label>
                                <input class="form-control" name="username" data-bind="value: username"/>
                                <label for="password">
                                    Password
                                </label>
                                <input class="form-control" name="password" data-bind="value: password" type="password"/>
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
