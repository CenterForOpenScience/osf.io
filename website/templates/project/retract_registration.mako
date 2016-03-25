<%inherit file="project/project_base.mako"/>
<%def name="title()">Withdraw Registration of Component</%def>

<legend class="text-center">Withdraw Registration</legend>

    <div id="registrationRetraction" class="col-md-6 col-md-offset-3">
        <div class="panel panel-default">
            <div class="panel-body">
                Withdrawing a registration will remove its content from the OSF, but leave basic metadata behind.
                The title of a withdrawn registration and its contributor list will remain, as will justification or
                explanation of the withdrawal, should you wish to provide it. Withdrawn registrations will be marked
                with a "withdrawn" tag. <strong>This action is irreversible.</strong>
            </div>
        </div>
        <form id="registrationRetractionForm" role="form">

            <div class="form-group">
                <label class="control-label">Please provide your justification for withdrawing this registration.</label>
                <textarea
                        class="form-control"
                        data-bind="textInput: justification"
                        id="justificationInput"
                        autofocus
                        >
                </textarea>
            </div>

            <hr />

            <div class="form-group">
                <label style="font-weight:normal" class="control-label">
                    Type <span data-bind="text: truncatedTitle" style="font-weight:bold"></span> and click Withdraw Registration if you are sure you want to continue.
                </label>
                <input  type="text"
                        class="form-control"
                        data-bind="textInput: confirmationText"
                />

            </div>
            <button type="submit" class="btn btn-danger" data-bind="click: submit, css: {disabled: !valid()}">Withdraw Registration</button>
            <div class="m-t-md" data-bind="css: messageClass, html: message"></div>
        </form>
    </div>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${'/static/public/js/registration-retraction-page.js' | webpack_asset}"></script>
</%def>
