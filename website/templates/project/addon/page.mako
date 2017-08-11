<%inherit file="../project_base.mako" />

<h4>
    ${full_name} Add-on
    % if capabilities:
        <span class="addon-capabilities">
            <i class="fa fa-question-circle"></i>
        </span>
    % endif
</h4>

% if complete:

    <div class="addon-content">
        ${self.body()}
    </div>

% else:

    <div class='addon-config-error p-sm'>
        ${full_name} add-on is not configured properly.
        % if user['is_contributor']:
            Configure this add-on on the <a href="${node['url']}settings/">settings</a> page.
        % endif
    </div>


% endif

<script id="capabilities" type="text/html">${addon_capabilities}</script>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    % for style in addon_page_css or []:
        <link rel="stylesheet" href="${style}" />
    % endfor
</%def>

<%def name="javascript_bottom()">

    ${parent.javascript_bottom()}

    % for script in addon_page_js or []:
        <script type="text/javascript" src="${script}"></script>
    % endfor

    <script type="text/javascript">
        // Show capabilities modal on addon widget help
        $('.addon-capabilities').on('click', function() {
            bootbox.alert({
                message:$('#capabilities').html(),
                buttons:{
                    ok:{
                        label:'Close',
                        className:'btn-default'
                    }
                }
            });
        });
    </script>

</%def>
