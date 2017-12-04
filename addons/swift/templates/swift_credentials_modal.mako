<div id="swiftInputCredentials" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>Connect an Swift Account</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">
                        <div class="col-sm-3"></div>

                        <div class="col-sm-6">
                            <div class="form-group">
                                <label for="swiftAddon">Authentication(Keystone) Version</label>
                                <select class="form-control" data-bind="value: authVersion, options: ['v2', 'v3']" id="auth_version" name="auth_version" ${'disabled' if disabled else ''} ></select>
                            </div>
                            <div class="form-group">
                                <label for="swiftAddon">Authentication URL</label>
                                <input class="form-control" data-bind="value: authUrl" id="auth_url" name="auth_url" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="swiftAddon">Tenant name</label>
                                <input class="form-control" data-bind="value: tenantName" id="tenant_name" name="tenant_name" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="swiftAddon">Project Domain name</label>
                                <input class="form-control" data-bind="value: projectDomainName, enable: authVersion() == 'v3'" id="project_domain_name" name="project_domain_name" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="swiftAddon">Username</label>
                                <input class="form-control" data-bind="value: accessKey" id="access_key" name="access_key" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="swiftAddon">User Domain name</label>
                                <input class="form-control" data-bind="value: userDomainName, enable: authVersion() == 'v3'" id="user_domain_name" name="user_domain_name" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="swiftAddon">Password</label>
                                <input type="password" class="form-control" data-bind="value: secretKey" id="secret_key" name="secret_key" ${'disabled' if disabled else ''} />
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
