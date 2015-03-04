<%inherit file="project/project_base.mako"/>
<%def name="title()">Retract Registration of Component</%def>

<legend class="text-center">Retract Registration</legend>

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
        </form>
    </div>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${'/static/public/js/registration-retraction-page.js' | webpack_asset}"></script>
</%def>