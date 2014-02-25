<%inherit file="base.mako"/>
<%def name="title()">Register Component</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<legend class="text-center">Register</legend>

% if schema:

    <%include file="metadata/register_${str(metadata_version)}.mako" />

% else:

    <form role="form">

        <div class="help-block">${language.registration_info}</div>

        <select class="form-control" id="select-registration-template">
            <option>Please select a registration form to initiate registration</option>
            % for option in options:
                <option value="${option['template_name']}">${option['template_name_clean']}</option>
            % endfor
        </select>
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
