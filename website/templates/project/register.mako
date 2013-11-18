<%inherit file="base.mako"/>
<%def name="title()">Register Component</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<legend class="text-center">Register</legend>

% if schema:

    <%include file="metadata/register_${str(metadata_version)}.mako" />

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
            if (val != 'Please select')
                window.location.href += val;
        });
    </script>

% endif

</%def>
