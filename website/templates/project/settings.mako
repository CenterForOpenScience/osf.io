<%inherit file="base.mako"/>
<%def name="title()">Project Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

##<!-- Show API key settings -->
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "${node["api_url"]}keys/",
##        "replace": true,
##        "kwargs": {
##            "route": "${node["url"]}"
##        }
##    }'></div>

<div class="row">
    <div class="col-md-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="#configureNode">Configure ${node['category'].capitalize()}</a></li>
                <li><a href="#selectAddons">Select Add-ons</a></li>
                % if addon_enabled_settings:
                    <li><a href="#configureAddons">Configure Add-ons</a></li>
                % endif
            </ul>
        </div><!-- end sidebar -->
    </div>
    <div class="col-md-6">

        <div id="configureNode" class="panel panel-default">

            <div class="panel-heading">
                <h3 class="panel-title">Configure ${node['category'].capitalize()}</h3>
            </div>

            <div class="panel-body">

                <!-- Delete node -->
                <button id="delete-node" class="btn btn-danger">Delete ${node['category']}</button>

            </div>

        </div>

        <div id="selectAddons" class="panel panel-default">

            <div class="panel-heading">
                <h3 class="panel-title">Select Add-ons</h3>
            </div>

            <div class="panel-body">

                <form id="selectAddonsForm">

                    % for category in addon_categories:

                        <%
                            addons = [
                                addon
                                for addon in addons_available
                                if category in addon.categories
                            ]
                        %>

                        % if addons:
                            <h3>${category.capitalize()}</h3>
                            % for addon in addons:
                                <div>
                                    <label>
                                        <input
                                            type="checkbox"
                                            name="${addon.short_name}"
                                            class="addon-select"
                                            ${'checked' if addon.short_name in addons_enabled else ''}
                                            ${'disabled' if node['is_registration'] else ''}
                                        />
                                        ${addon.full_name}
                                    </label>
                                </div>
                            % endfor
                        % endif

                    % endfor

                    <br />

                    % if not node['is_registration']:
                        <button id="settings-submit" class="btn btn-success">
                            Submit
                        </button>
                        <div class="addon-settings-message text-success" style="padding-top: 10px;"></div>
                    % endif

                </form>

            </div>
        </div>

        % if addon_enabled_settings:

            <div id="configureAddons" class="panel panel-default">

                <div class="panel-heading">
                    <h3 class="panel-title">Configure Add-ons</h3>
                </div>

                <div class="panel-body">

                    % for name in addon_enabled_settings or []:

                        <div mod-meta='{
                                "tpl": "../addons/${name}/templates/${name}_node_settings.mako",
                                "uri": "${node['api_url']}${name}/settings/"
                            }'></div>

                        % if not loop.last:
                            <hr />
                        % endif

                    % endfor

                </div>
            </div>

        % endif

    </div>

</div>

<!-- Include metadata templates -->
<%include file="metadata/metadata_templates_1.html" />

% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${capabilities}</script>
% endfor

</%def>

<%def name="javascript_bottom()">

<script type="text/javascript" src="/static/js/metadata_1.js"></script>

## TODO: Move to project.js
<script type="text/javascript">

    ## TODO: Replace with something more fun, like the name of a famous scientist
    ## h/t @sloria
    function randomString() {
        var alphabet = 'abcdefghijkmnpqrstuvwxyz23456789',
            text = '';

        for (var i = 0; i < 5; i++)
            text += alphabet.charAt(Math.floor(Math.random() * alphabet.length));

        return text;
    }

    $(document).ready(function() {

        // Set up submission for addon selection form
        $('#selectAddonsForm').on('submit', function() {

            var formData = {};
            $('#selectAddonsForm').find('input').each(function(idx, elm) {
                var $elm = $(elm);
                formData[$elm.attr('name')] = $elm.is(':checked');
            });
            var msgElm = $(this).find('.addon-settings-message');
            $.ajax({
                url: nodeApiUrl + 'settings/addons/',
                data: JSON.stringify(formData),
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json',
                success: function() {
                    msgElm.text('Settings updated').fadeIn();
                    window.location.reload();
                }
            });

            return false;

        });

        $('#delete-node').on('click', function() {
            var key = randomString();
            bootbox.prompt(
                '<div>Delete this ${node['category']} and all non-project children? This is IRREVERSIBLE.</div>' +
                    '<p style="font-weight: normal; font-size: medium; line-height: normal;">If you want to continue, type <strong>' + key + '</strong> and click OK.</p>',
                function(result) {
                    if (result === key) {
                        window.location.href = '${node['url']}remove/';
                    }
                }
            )
        });

        // Show capabilities modal on selecting an addon; unselect if user
        // rejects terms
        $('.addon-select').on('change', function() {
            var that = this,
                $that = $(that);
            if ($that.is(':checked')) {
                var name = $that.attr('name'),
                    capabilities = $('#capabilities-' + name);
                if (capabilities) {
                    bootbox.confirm(
                        capabilities.html(),
                        function(result) {
                            if (!result) {
                                $(that).attr('checked', false);
                            }
                        }
                    )
                }
            }
        });

    });

</script>

</%def>