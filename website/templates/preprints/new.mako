<%inherit file="base.mako"/>
<%def name="title()">New Preprint</%def>
<%def name="content()">
    <h2 class="page-title text-center">Create New Preprint Project</h2>
    <div id="newPreprintScope" class="img-rounded centered col-md-6 scripted">
        <pre data-bind="text: ko.toJSON($data, null, 2)"></pre>

        <form data-bind="submit: submit, css: {hideValidation: !showValidation()}">

            <div
                    class="form-group"
                    data-bind="css: {'has-error': paperName() && !paperName.isValid()}">
                <input
                        class="form-control"
                        placeholder="Paper Name"
                        data-bind="value: paperName,
                                       valueUpdate: 'input',
                                       disable: submitted(),
                                       event: {
                                           focus: hideValidation,
                                           blur: trim.bind($data, paperName)
                                       }"
                        />
            </div>

            <div
                    class="form-group">
                <input
                        class="form-control"
                        type="file"
                        data-bind="value: file"
                        />
            </div>


            <!-- Flashed Messages -->
            <div class="help-block">
                <p data-bind="html: flashMessage, attr.class: flashMessageClass"></p>
            </div>

            <div>
                <button
                        type="submit"
                        class="btn btn-danger"
                        data-bind="visible: !submitted()"
                        >Create Preprint Project</button>
            </div>

        </form>

    </div><!-- end #signUpScope -->
</%def>

<%def name="stylesheets()">
    <link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/jquery-ui.css">
</%def>

<%def name="javascript_bottom()">
    <script>
        $script(['/static/js/new_preprint.js']);
        $script.ready('newPreprint', function() {
            var newPreprint = new NewPreprint(
                    '#newPreprintScope',
                    '${api_url_for('preprint_new')}'
            );
        });
    </script>
</%def>