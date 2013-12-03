<script type="text/javascript" src="/static/js/metadata_1.js"></script>

<div class="col-md-6 col-md-offset-3" id="registration_template">

    <%include file="metadata_1.html" />

    <form class="form">

        % if not registered:

            <div id="register-show-submit" data-bind="visible:$root.isLast()">

                <hr />

                <p class="help-block">
                    Registration cannot be undone, and the archived content and
                    files cannot be deleted after registration. Please be sure the
                    project is complete and comprehensive for what you wish to
                    register.
                </p>

                <div class="form-group">
                    <label>
                        Type "continue" if you are sure you want to continue
                    </label>
                    <div class="controls">
                        <input class="form-control" data-bind="value:$root.continueText, valueUpdate: 'afterkeydown'" />
                    </div>
                </div>

            </div>

        % endif

        % if not registered:
            <button id="register-submit" class="btn btn-success" data-bind="visible:$root.continueFlag, focus:$root.continueFlag">
                Register
            </button>
        % endif

    </form>

</div><!-- end #registration_template -->

<!-- Apply view model -->
<script type="text/javascript">

    /**
     * Unblock UI and display error modal
     */
    function registration_failed() {
        unblock();
        bootbox.alert('Registration failed');
    }

    $(document).ready(function() {

        registrationViewModel = new MetaData.ViewModel(
            ${schema},
            ${int(registered)},
            ${[str(node['id'])] + node['children_ids']}
        );
        ko.applyBindings(registrationViewModel, $('#registration_template')[0]);
        registrationViewModel.updateIdx('add', true);

        % if registered:
            registrationViewModel.unserialize(${payload});
        % endif

        $('#registration_template form').on('submit', function() {

            // Serialize responses
            var serialized = registrationViewModel.serialize(),
                data = serialized.data,
                complete = serialized.complete;

            // Clear continue text and stop if incomplete
            if (!complete) {
                registrationViewModel.continueText('');
                return false;
            }

            // Block UI until request completes
            block();

            // POST data
            $.ajax({
                url: '${node['api_url']}' + 'register/' + '${template_name if template_name else ''}/',
                type: "POST",
                data: JSON.stringify(data),
                contentType: "application/json",
                dataType: 'json'
            }).done(function(response) {
                if (response.status === 'success')
                    window.location.href = response.result;
                else if (response.status === 'error')
                    registration_failed();
            }).fail(function() {
                registration_failed();
            });

            // Stop event propagation
            return false;

        });

    });

</script>