<div id="s3InputCredentials" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>Connect an Amazon S3 Account</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">
                        <div class="col-sm-3"></div>

                        <div class="col-sm-6">
                            <div class="form-group">
                                <label for="s3Addon">Nickname</label>
                                <input class="form-control" data-bind="value: nickname" id="_nickname" name="_nickname" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="s3Addon">Host</label>
                                <input class="form-control" data-bind="value: host" id="_host" name="_host" ${'disabled' if disabled else ''} />
                            </div>

                            <div class="form-group">
                                <label for="s3Addon">Port</label>
                                <input class="form-control" data-bind="value: port" id="_port" name="_port" ${'disabled' if disabled else ''} />
                            </div>

                            <div class="form-group">
                                <label for="s3Addon">Access Key</label>
                                <input class="form-control" data-bind="value: accessKey" id="access_key" name="access_key" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="s3Addon">Secret Key</label>
                                <input type="password" class="form-control" data-bind="value: secretKey" id="secret_key" name="secret_key" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="s3Addon">Use TLS Encryption</label>
                                <input class="form-control" type="checkbox" data-bind="checked: encrypted" id="encrypted" name="encrypted" ${'disabled' if disabled else ''} />
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
