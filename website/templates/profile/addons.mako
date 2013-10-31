<%inherit file="base.mako"/>
<%def name="title()">Addons</%def>
<%def name="content()">
<div mod-meta='{"tpl": "include/subnav.mako", "replace": true}'></div>

<h2>Addons</h2>

##% for addon_id in addon_ids:
##    Render addon here
##% endfor

<h3>Create addon</h3>

<form id="select-addon">
    <select name="addon-type">
        <option>---</option>
        <option value="dataverse" data-form-uri="/api/v1/dataverse/get_user_settings_form/">Dataverse</option>
        <option value="github">GitHub</option>
        <option value="s3">Amazon S3</option>
    </select>
</form>

<div id="create-addon">...</div>

<script type="text/javascript">
    $('#select-addon').on('change', function() {
        var form_uri = $(this).find(':selected').attr('data-form-uri');
        if (form_uri) {
            $.get(
                form_uri,
                function(result) {
                    $('#create-addon').html(result);
                }
            );
        } else {
            $('#create-addon').html('');
        }
        return false;
    });
</script>

</%def>
