<%inherit file="project/project_base.mako"/>
<%def name="title()">Register Component</%def>

<legend class="text-center">Register</legend>

% if schema:
    <%include file="metadata/register_${str(metadata_version)}.mako" />
% else:

    <form role="form">

        <div class="help-block">${language.REGISTRATION_INFO}</div>

        <select class="form-control" id="select-registration-template">
            <option value="">Please select a registration form to initiate registration</option>
            % for option in options:
                <option value="${option['template_name']}">${option['template_name_clean']}</option>
            % endfor
        </select>
    </form>


    <script type="text/javascript">
        $('#select-registration-template').on('change', function() {
            var $this = $(this);
            var val = $this.val();
            if (val !== '') {
                var urlparse = window.location.href.split("?");
                urlparse[0] += '/' + val;
                window.location.href = urlparse.join("?")
            }
        });
    </script>

% endif

<%def name="javascript_bottom()">
  ${parent.javascript_bottom()}
  % if schema:
    <script src="/static/public/js/register_${str(metadata_version)}-page.js"></script>
  % endif
</%def>
