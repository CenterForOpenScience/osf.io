<div id="boaCredentialsModal" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">

            <div class="modal-header">
                <h3>Connect a Boa Account</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">

                        <div class="col-sm-6">
                            <!-- API Token Input-->
                            <div class="form-group"">
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
                              <em>These credentials will be encrypted.</em>
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
