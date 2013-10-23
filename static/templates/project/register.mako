<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>

<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div mod-meta='{
        "tpl": "metadata/knockout.mako",
        "replace": true
    }'></div>

<legend>Register</legend>

% if schema:

    <!-- Build registration form -->
    <form id="register" method="POST" class="form-horizontal">

        <!-- Auto-generated contect from Knockout -->
        <div data-bind="foreach:schema">
            <div class="control-group">
                <label class="control-label" data-bind="text:$data.label, attr:{for:$data.id}"></label>
                <div class="controls">
                    <div data-bind='item:$data, attr:{id:$data.id}'></div>
                </div>
            </div>
        </div>

        % if not registered:

            <!-- Register the node -->
            <p>
                Registration cannot be undone, and the archived content and
                files cannot be deleted after registration. Please be sure the
                project is complete and comprehensive for what you wish to
                register.
            </p>

            <div class="control-group">
                <label class="control-label">
                    Type "continue" if you are sure you want to continue
                </label>
                <div class="controls">
                    <input data-bind="value:continueText, valueUpdate: 'afterkeydown'" />
                </div>
            </div>
            <div class="control-group">
                <div class="controls">
                    <input data-bind="visible:continueFlag" type="submit" value="Register" class="btn" />
                </div>
            </div>

        % endif

    </form>

    <!-- Apply view model -->
    <script type="text/javascript">
        var view_model = new ViewModel(${schema});
        ko.applyBindings(view_model, $('#register')[0]);
    </script>

    <script type="text/javascript">

        $('#register').on('submit', function() {
            var $this = $(this),
                data = {};
            $this.serializeArray().forEach(function(elm) {
                data[elm.name] = elm.value;
            });
			$.post(
                '${node_api_url}' + 'register/' + '${template_name if template_name else ''}/',
                {data: JSON.stringify(data)},
                function(response) {
                    if (response.status === 'success')
                        window.location.href = response.result;
                    else if (response.status === 'error')
                        window.location.reload();
                },
                'json'
            );
            return false;
        });

    </script>

% else:

    <form>

        <select id="select-registration-template">
            <option>Please select</option>
            % for option in options:
                <option value="${option['template_name']}">${option['template_name_clean']}</option>
            % endfor
        </select>

    </form>

    <p>
        Registration will create a frozen version of the project as it exists
        right now.  You will still be able to make revisions to the project,
        but the frozen version will be read-only, have a unique url, and will
        always be associated with the project.
    </p>

    <script type="text/javascript">
        $('#select-registration-template').on('change', function() {
            var $this = $(this),
                val = $this.val();
            if (val)
                window.location.href += val;
        });
    </script>

% endif

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>