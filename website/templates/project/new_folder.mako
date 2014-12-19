<%inherit file="base.mako"/>
<%def name="title()">Create New Folder</%def>
<%def name="content()">

    <h2 class="page-title text-center">Create New Folder</h2>

    <form id="creationForm" data-bind="submit: verifyTitle">
        <div class="row">
            <div class="col-md-6 col-md-offset-3">
                <label for="title">Title</label>
                <input class="form-control" type="text" name="title" data-bind="value: title">
                <span class="validationMessage" data-bind="text: formErrorText"></span><br />
            </div>
        </div>
        <br />
        <div class="row">
            <div class="col-md-6 col-md-offset-3">
                <button class="btn btn-primary" type="submit">Create New Folder</button>
            </div>
        </div>
    </form>
</%def>

<%def name="stylesheets()">
    <link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/jquery-ui.css">
</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script>
    window.contextVars = window.contextVars || {};
    window.contextVars.nodeID = '${node_id}';
</script>
<script src="/static/public/js/new-folder-page.js"></script>
</%def>

