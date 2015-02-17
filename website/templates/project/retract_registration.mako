<%inherit file="project/project_base.mako"/>
<%def name="title()">Retract Registration of Component</%def>

<legend class="text-center">Retract Registration</legend>

% if schema:
    <%include file="metadata/register_${str(metadata_version)}.mako" />
% else:

    <div id="registrationRetraction" class="col-md-6 col-md-offset-3">
        <form id="registration_retraction_form" role="form">

            <div class="form-group">
                <label class="control-label">Please provide your justification for retracting this registration.</label>
                <textarea
                        class="form-control"
                        data-bind="textInput: justification"
                        id="justificationInput"
                        >

                </textarea>
            </div>

            <hr />

            <div class="form-group">
                <label class="control-label">Type '<span data-bind="text: registrationTitle"></span>' if you are sure you want to continue.</label>
                <textarea
                        class="form-control"
                        data-bind="textInput: confirmationText"
                        >

                </textarea>
            </div>
            <button type="submit" class="btn btn-danger" data-bind="click: submit, visible: true">Retract Registration</button>

            <hr />
            ## NOTE(hrybacki): knockout viewmodel dump for testing purposes
            <pre data-bind="text: ko.toJSON($data, null, 2)"></pre>

    ##        <div class="help-block">${language.REGISTRATION_INFO}</div>
    ##
    ##        <select class="form-control" id="select-registration-template">
    ##            <option value="">Please select a registration form to initiate registration</option>
    ##            % for option in options:
    ##                <option value="${option['template_name']}">${option['template_name_clean']}</option>
    ##            % endfor
    ##        </select>
        </form>
    </div>
##    <!-- Todo(hrybacki): This should be converted to a knockout script -->
##    <script type="text/javascript">
##        $('#select-registration-template').on('change', function() {
##            var $this = $(this);
##            var val = $this.val();
##            if (val !== '') {
##                var urlparse = window.location.href.split("?");
##                urlparse[0] += '/' + val;
##                window.location.href = urlparse.join("?")
##            }
##        });
##    </script>

% endif

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${'/static/public/js/registration-retraction-page.js' | webpack_asset}"></script>
</%def>