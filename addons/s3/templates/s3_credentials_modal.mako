<div id="s3InputCredentials" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>Connect S3 Object Storage</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">
                        <div class="col-sm-3"></div>

                        <div class="col-sm-6">
                            <h4>OSF Addon Settings</h4>
                            <div class="form-group">
                                <label for="s3Addon">Nickname</label>
                                <input class="form-control" data-bind="value: nickname" id="_nickname" name="_nickname" ${'disabled' if disabled else ''} />
                            </div>
                            <h4>Account Credentials</h4>
                            <div class="form-group">
                                <label for="s3Addon">Access Key</label>
                                <input class="form-control" data-bind="value: accessKey" id="access_key" name="access_key" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="s3Addon">Secret Key</label>
                                <input type="password" class="form-control" data-bind="value: secretKey" id="secret_key" name="secret_key" ${'disabled' if disabled else ''} />
                            </div>
                            <h4 data-bind="click: toggleAdvanced" class='advanced_settings_heading'>
                                <span class=" fa fa-caret-right"></span>
                                Advanced Settings
                            </h4>
                            <div class='advanced_settings' style="display: none">
                                <p>Advanced settings are optional and may be left blank; they will default to AWS s3. Many third party storage providers use the same instructions as and are compatible with AWS S3. To use an s3-compatible provider instead of the default, enter a host, port, and mark wheter or not the provider uses an encrypted connection.</p>
                                <div class="form-group">
                                    <label for="s3Addon">Host</label>
                                    <input class="form-control" data-bind="value: host" id="_host" name="_host" ${'disabled' if disabled else ''} />
                                </div>

                                <div class="form-group">
                                    <label for="s3Addon">Port</label>
                                    <input class="form-control" data-bind="value: port" id="_port" name="_port" ${'disabled' if disabled else ''} />
                                </div>
                                <div class="form-group encrypted">
                                    <label class="form-check-label" for="encrypted">
                                        Use TLS Encryption<br>
                                        <input class="form-check-input" type="checkbox" id="encrypted" name="encrypted" data-lpignore=true autocomplete=off />
                                    </label>
                                </div>
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
