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
                                <input type="checkbox" data-bind="checked: binderhubHasOAuthClient" name="binderhub_has_oauth_client" ${'disabled' if disabled else ''} />
                                <label for="binderhubAddon">${_("Use BinderHub API")}</label>
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("BinderHub OAuth Client ID")}</label>
                                <input class="form-control" data-bind="value: binderhubOAuthClientId, disable: binderhubOAuthDisabled" name="binderhub_oauth_client_id" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("BinderHub OAuth Client Secret")}</label>
                                <input type="password" class="form-control" data-bind="value: binderhubOAuthClientSecret, disable: binderhubOAuthDisabled" name="binderhub_oauth_client_secret" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <input type="checkbox" data-bind="checked: jupyterhubHasOAuthClient" name="jupyterhub_has_oauth_client" ${'disabled' if disabled else ''} />
                                <label for="binderhubAddon">${_("Use JupyterHub API")}</label>
                            </div>
                            <div class="form-group">
                                <label for="jupyterhubAddon">${_("JupyterHub URL")}</label>
                                <input class="form-control" data-bind="value: jupyterhubUrl, disable: jupyterhubOAuthDisabled" name="jupyterhub_url" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("JupyterHub OAuth Client ID")}</label>
                                <input class="form-control" data-bind="value: jupyterhubOAuthClientId, disable: jupyterhubOAuthDisabled" name="jupyterhub_oauth_client_id" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("JupyterHub OAuth Client Secret")}</label>
                                <input type="password" class="form-control" data-bind="value: jupyterhubOAuthClientSecret, disable: jupyterhubOAuthDisabled" name="jupyterhub_oauth_client_secret" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("JupyterHub Admin Token")}</label>
                                <input type="password" class="form-control" data-bind="value: jupyterhubAdminAPIToken, disable: jupyterhubOAuthDisabled" name="jupyterhub_admin_api_token" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("JupyterHub Logout URL")}</label>
                                <input class="form-control" data-bind="value: jupyterhubLogoutUrl, disable: jupyterhubOAuthDisabled" name="jupyterhub_logout_url" ${'disabled' if disabled else ''} />
                            </div>
                            <div class="form-group">
                                <label for="binderhubAddon">${_("Maximum number of servers available on JupyterHub")}</label>
                                <input class="form-control" data-bind="value: jupyterhubMaxServers, disable: jupyterhubOAuthDisabled" name="jupyterhub_max_servers" ${'disabled' if disabled else ''} />
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
                        <!-- ko if: jupyterhubMaxServersInvalid() -->
                        <p class='text-danger'>
                          ${_("Maximum number of servers must be a number or an empty string.")}
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
