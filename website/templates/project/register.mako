<%inherit file="base.mako"/>
<%def name="title()">Register Component</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<legend class="text-center">Register</legend>

% if schema:

##    <%include file=register_${version} />
    <script type="text/javascript" src="${appjs}"></script>

    <div class="col-md-6 col-md-offset-3" id="registration_template">

        <%include file="${apphtml}"/>

        <form class="form">
##
##            <div data-bind="foreach:questions">
##                <div class="form-group">
##                    <label class="control-label" data-bind="text:$data.label, attr:{for:$data.id}"></label>
##                    <div class="controls">
##                        <div data-bind='item:$data, attr:{id:$data.id}'></div>
##                    </div>
##                </div>
##            </div>
##
##            <!-- Pagination -->
##            <div data-bind="visible:$parent.npages > 1">
##                <div class="form-group">
##                    <div class="controls">
##                        <button class="btn" data-bind="click:$parent.previous, disable:$parent.isFirst()">Previous</button>
##                        <span class="progress-meter" style="padding: 0px 10px 0px 10px;">
##                            Page <span data-bind="text:$parent.currentIndex() + 1"></span>
##                            of <span data-bind="text:$parent.npages"></span>
##                        </span>
##                        <button class="btn" data-bind="click:$parent.next, disable:$parent.isLast()">Next</button>
##                    </div>
##                </div>
##            </div>
##
            % if not registered:

                <div id="register-show-submit" data-bind="visible:$root.isLast()">
##                <div id="register-show-submit">

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
##            var viewModel = new MetaData.ViewModel(${schema}, ${int(registered)});
            ko.applyBindings(viewModel, $('#registration_template')[0]);
            viewModel.updateIdx('add', true);
            % if registered:
                viewModel.unserialize(${payload});
            % endif
            $('#register-submit').on('click', function() {
##            $('#register-submit form').on('click', function() {
                var $this = $(this);
                if (!$this.hasClass('disabled')) {
                    $this.addClass('disabled');
                    $this.closest('form').submit();
                }
                return false;
            });

##            $('#registration_template').on('submit', function(event) {
            $('#registration_template form').on('submit', function() {

                // Initialize variables
                var $this = $(this);
##                    data = {};
##
##                // Grab data from view model
##                $.each(viewModel.pages(), function(_, page) {
##                    $.each(page.questions, function(_, question) {
##                        data[question.id] = question.value;
##                    });
##                });
                var data = viewModel.serialize().data;
                console.log('got data ' + JSON.stringify(data));
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
                    dataType: 'json'
                });

                // Stop event propagation
                return false;

            });
        });
    </script>

% else:

    <form role="form">

        <select class="form-control" id="select-registration-template">
            <option>Please select</option>
            % for option in options:
                <option value="${option['template_name']}">${option['template_name_clean']}</option>
            % endfor
        </select>
        <span class="help-block">Registration will create a frozen version of the project as it exists
        right now.  You will still be able to make revisions to the project,
        but the frozen version will be read-only, have a unique url, and will
        always be associated with the project.</span>
    </form>


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
