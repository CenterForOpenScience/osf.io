<%inherit file="preprints/base.mako"/>
<%def name="title()">New Preprint</%def>
<%def name="content()">
    <h2 class="page-title text-center">Create New Preprint Project</h2>
    <div id="newPreprintScope" class="img-rounded centered col-md-6 scripted">
##        <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> ## for debugging



        <form action="${api_url_for('post_preprint_new')}" method="post" enctype="multipart/form-data">
            <input type="file" name="file" />
            <input type="submit" class="btn" value="Upload File"/>
        </form>

    </div>
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
                    '${api_url_for('post_preprint_new')}'
            );
        });
    </script>
</%def>