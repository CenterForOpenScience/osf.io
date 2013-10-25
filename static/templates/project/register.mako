<%inherit file="base.mako"/>
<%def name="title()">Register Component</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div mod-meta='{
        "tpl": "metadata/knockout.mako",
        "replace": true
    }'></div>

<legend>Register</legend>

% if schema:

    <div id="registration_template" data-bind="with:currentPage">

        <h2 data-bind="text:$data.title"></h2>
        <br />

        <form class="form-horizontal">

            <div data-bind="foreach:questions">
                <div class="control-group">
                    <label class="control-label" data-bind="text:$data.label, attr:{for:$data.id}"></label>
                    <div class="controls">
                        <div data-bind='item:$data, attr:{id:$data.id}'></div>
                    </div>
                </div>
            </div>

            <!-- Pagination -->
            <div data-bind="visible:$parent.npages > 1">
                <div class="control-group">
                    <div class="controls">
                        <button class="btn" data-bind="click:$parent.previous, disable:$parent.isFirst()">Previous</button>
                        <span class="progress-meter" style="padding: 0px 10px 0px 10px;">
                            Page <span data-bind="text:$parent.currentIndex() + 1"></span>
                            of <span data-bind="text:$parent.npages"></span>
                        </span>
                        <button class="btn" data-bind="click:$parent.next, disable:$parent.isLast()">Next</button>
                    </div>
                </div>
            </div>

            % if not registered:

                <div id="register-show-submit" data-bind="visible:$parent.isLast()">

                    <hr />

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
                            <input data-bind="value:$parent.continueText, valueUpdate: 'afterkeydown'" />
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="controls">
                            <button id="register-submit" class="btn" data-bind="visible:$parent.continueFlag">
                                Register
                            </button>
                        </div>
                    </div>

                </div>

            % endif

        </form>

    </div>

    <!-- Apply view model -->
    <script type="text/javascript">
        var viewModel = new ViewModel(${schema}, ${int(registered)});
        ko.applyBindings(viewModel, $('#registration_template')[0]);
    </script>

    <script type="text/javascript">

        $('#register-submit').on('click', function() {
            var $this = $(this);
            if (!$this.hasClass('disabled')) {
                $this.addClass('disabled');
                $this.closest('form').submit();
            }
            return false;
        });

        $('#registration_template').on('submit', function(event) {

            // Initialize variables
            var $this = $(this),
                data = {};

            // Grab data from view model
            $.each(viewModel.pages(), function(_, page) {
                $.each(page.questions, function(_, question) {
                    data[question.id] = question.value;
                });
            });

            // Send data to OSF
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

            // Stop event propagation
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

</%def>