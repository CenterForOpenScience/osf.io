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
                            <div data-bind="if: hasDefaultHosts">
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
                            </div>

                            <!-- Custom input -->
                            <div data-bind="if: useCustomHost">
                                <label>Host URL</label>
                                <div class="input-group form-group">
                                    <div class="input-group-addon">https://</div>
                                    <input type="text" class="form-control" name="customHost" data-bind="value: customHost" placeholder="owncloud.example.org">
                                </div>
                                <div class="text-muted" style="text-align: center">
                                    <em>Only ownCloud instances supporting <a href="https://doc.owncloud.org/server/9.1/user_manual/files/access_webdav.html" target="_blank">WebDAV</a> and <a href="https://www.freedesktop.org/wiki/Specifications/open-collaboration-services-1.7/" target="_blank">
                                        OCS v1.7</a> are supported.
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
                                <input class="form-control" name="username" data-bind="value: username" placeholder="username" />
                                <label for="password">
                                    Password
                                </label>
                                <input class="form-control" name="password" data-bind="value: password" type="password" placeholder="********" />
                            </div>
                            <div class="text-muted" style="text-align: center">
                                <em> These credentials will be encrypted. However, we <strong>strongly encourage</strong> using a <a href="https://doc.owncloud.org/server/9.1/user_manual/session_management.html#managing-devices" target="_blank"> Device (or App) Password</a>.
                                </em>
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
                    <button data-bind="click: connectAccount" class="btn btn-success">Save</button>

                </div><!-- end modal-footer -->

            </form>

        </div><!-- end modal-content -->
    </div>
</div>
