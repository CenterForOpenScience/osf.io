<%inherit file="base.mako"/>
<%def name="title()">Create New Folder</%def>
<%def name="content()">

<h2 class="page-title text-center">Create New Folder</h2>
<div class="row">
    <div class="col-md-6 col-md-offset-3">
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/new_folder/",
                "kwargs": {
                    "name": "newFolder",
                    "method_string": "POST",
                    "action_string": "/folder/new/${node_id}",
                    "form_class": "form-stacked",
                    "submit_string": "Create New Folder",
                    "id": "folderForm",
                    "submit_btn_class": "btn-primary"
                },
                "replace": true
            }'>
        </div>
    </div>
</div><!-- end row -->
</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/jquery-ui.css">
</%def>

<%def name="javascript_bottom()">
<script>
    // TODO(sloria): require('jquery') here
    //block the create new project button when the form is submitted
    $('#folderForm').on('submit',function(){
        $('button[type="submit"]', this)
            .attr('disabled', 'disabled')
            .text('Creating');
    });
</script>
</%def>
