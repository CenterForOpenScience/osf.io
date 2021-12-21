<div id="binderhubInputHost" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>${_("Configure a BinderHub client")}</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">
                        <div class="col-sm-3"></div>

                        <div class="col-sm-6">
                            <div class="form-group">
                                <label for="binderhubAddon">${_("BinderHub URL")}</label>
                                <input class="form-control" data-bind="value: binderhubUrl" name="binderhub_url" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("BinderHub OAuth Client ID")}</label>
                                <input class="form-control" data-bind="value: binderhubOAuthClientId" name="binderhub_oauth_client_id" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("BinderHub OAuth Client Secret")}</label>
                                <input type="password" class="form-control" data-bind="value: binderhubOAuthClientSecret" name="binderhub_oauth_client_secret" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="jupyterhubAddon">${_("JupyterHub URL")}</label>
                                <input class="form-control" data-bind="value: jupyterhubUrl" name="jupyterhub_url" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("JupyterHub OAuth Client ID")}</label>
                                <input class="form-control" data-bind="value: jupyterhubOAuthClientId" name="jupyterhub_oauth_client_id" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("JupyterHub OAuth Client Secret")}</label>
                                <input type="password" class="form-control" data-bind="value: jupyterhubOAuthClientSecret" name="jupyterhub_oauth_client_secret" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("JupyterHub Admin Token")}</label>
                                <input type="password" class="form-control" data-bind="value: jupyterhubAdminAPIToken" name="jupyterhub_admin_api_token" ${'disabled' if disabled else ''} />
                            </div>
                        </div>
                    </div><!-- end row -->

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <!-- ko if: binderhubUrlInvalid() -->
                        <p class='text-danger'>
                          ${_("BinderHub URL is invalid. BinderHub URL should be start with http(s)://")}
                        </p>
                        <!-- /ko -->
                        <!-- ko if: jupyterhubUrlInvalid() -->
                        <p class='text-danger'>
                          ${_("JupyterHub URL is invalid. JupyterHub URL should be start with http(s)://")}
                        </p>
                        <!-- /ko -->
                    </div>

                </div><!-- end modal-body -->

                <div class="modal-footer">
                    <a href="#" class="btn btn-default" data-bind="click: clearModal" data-dismiss="modal">${_("Cancel")}</a>

                    <!-- Save Button -->
                    <button data-bind="click: addHost, enable: hostCompleted" class="btn btn-success">${_("Save")}</button>

                </div><!-- end modal-footer -->

            </form>

        </div><!-- end modal-content -->
    </div>
</div>
