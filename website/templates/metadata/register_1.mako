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
    $(document).ready(function() {
        schema = ${schema};
        viewModel = new MetaData.ViewModel(${schema}, ${int(registered)}, ${[str(node_id)] + node_children_ids});
        ko.applyBindings(viewModel, $('#registration_template')[0]);
        viewModel.updateIdx('add', true);
        % if registered:
            viewModel.unserialize(${payload});
        % endif
##        $('#register-submit').on('click', function() {
##            var $this = $(this);
##            if (!$this.hasClass('disabled')) {
##                $this.addClass('disabled');
##                $this.closest('form').submit();
##            }
##            return false;
##        });

        $('#registration_template form').on('submit', function() {

            var submitBtn = $('#register-submit');
            if (submitBtn.hasClass('disabled')) {
                return false;
            }

            var serialized = viewModel.serialize(),
                data = serialized.data,
                complete = serialized.complete;

            if (!complete) {
                viewModel.continueText('');
                return false;
            }

            submitBtn.addClass('disabled');

            // Send data to OSF
            $.ajax({
                url: '${node_api_url}' + 'register/' + '${template_name if template_name else ''}/',
                type: "POST",
                data: JSON.stringify(data),
                contentType: "application/json",
                success: function(response) {
                    if (response.status === 'success')
                        window.location.href = response.result;
                    else if (response.status === 'error')
                        window.location.reload();
                },
                fail: function() {
                    submitBtn.removeClass('disabled');
                },
                dataType: 'json'
            });

            // Stop event propagation
            return false;

        });
    });
</script>