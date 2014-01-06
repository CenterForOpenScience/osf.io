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
                <li><a href='#configureAddons'>Configure Addons</a></li>
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

        <div id="configureAddons" class="panel panel-default">

            <div class="panel-heading">
                <h3 class="panel-title">Configure Addons</h3>
            </div>

            <div class="panel-body">
                <form id="chooseAddonsForm">

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
                                            ${'checked' if addon.short_name in addons_enabled else ''}
                                            ${'disabled' if node['is_registration'] else ''}
                                        />
                                        ${addon.full_name}
                                    </label>
                                </div>
                            % endfor
                        % endif

                    % endfor

                    % if not node['is_registration']:
                        <button id="settings-submit" class="btn btn-success">
                            Submit
                        </button>
                    % endif

                </form>

                % if addon_settings:

                    <hr />

                    % for name in addon_enabled_settings:

                        <div>
                            <form class="addon-settings" data-addon="${name}">
                                <%include file="metadata/metadata_container_1.html" />
                                % if not node['is_registration']:
                                    <button id="settings-submit" class="btn btn-success">
                                        Submit
                                    </button>
                                % endif
                                <div>
                                    <br />
                                    <div class="message" style="display: none;"></div>
                                </div>
                            </form>
                        </div>

                        % if not loop.last:
                            <hr />
                        % endif

                    % endfor

                % endif

            </div>
        </div>

    </div>

</div>

<!-- Include metadata templates -->
<%include file="metadata/metadata_templates_1.html" />

</%def>

<%def name="javascript_bottom()">

<script type="text/javascript" src="/static/js/metadata_1.js"></script>

<script type="text/javascript">

    var addonSettingsModels = {};

    $(document).ready(function() {

        % for name in addon_enabled_settings:

            <% settings = addon_settings[name] %>

            var name = '${name}';

            // Set up view model
            var VM = new MetaData.ViewModel(
                ${settings['schema']},
                ${int(node['is_registration'])}
            );
            VM.updateIdx('add', true);

            // Add model to models hash
            addonSettingsModels[name] = VM;

            // Unserialize data from server
            VM.unserialize(${settings['settings']});

            // Apply completed bindings
            ko.applyBindings(
                VM,
                $('form.addon-settings[data-addon="${name}"]')[0]
            );

        % endfor

        ## TODO: Abstract authentication logic

        % if 'github' in addon_enabled_settings:

            var dataGH = addonSettingsModels.github.observedData,
                addButton = $('#githubAddKey'),
                delButton = $('#githubDelKey'),
                keyUser = $('#githubKeyUser');

            if (dataGH.github_code.value()) {
                delButton.show();
                keyUser.text('(Authorized by ' + dataGH.github_oauth_user.value() + ')');
            } else {
                addButton.show();
            }

            addButton.on('click', function() {
                window.location.href = nodeApiUrl + 'github/oauth/';
            });

            delButton.on('click', function() {
                bootbox.confirm(
                    'Are you sure you want to delete your GitHub access key?',
                    function(result) {
                        if (result) {
                            $.ajax({
                                url: nodeApiUrl + 'github/oauth/delete/',
                                type: 'POST',
                                contentType: 'application/json',
                                dataType: 'json',
                                success: function() {
                                    window.location.reload();
                                }
                            });
                        }
                    }
                )
            });

        % endif

        % if 'bitbucket' in addon_enabled_settings:

            var dataBB = addonSettingsModels.bitbucket.observedData,
                addButton = $('#bitbucketAddKey'),
                delButton = $('#bitbucketDelKey'),
                keyUser = $('#bitbucketKeyUser');

            if (dataBB.bitbucket_code.value()) {
                delButton.show();
                keyUser.text('(Authorized by ' + dataBB.bitbucket_oauth_user.value() + ')');
            } else {
                addButton.show();
            }

            addButton.on('click', function() {
                window.location.href = nodeApiUrl + 'bitbucket/oauth/';
            });

            delButton.on('click', function() {
                bootbox.confirm(
                    'Are you sure you want to delete your Bitbucket access key?',
                    function(result) {
                        if (result) {
                            $.ajax({
                                url: nodeApiUrl + 'bitbucket/oauth/delete/',
                                type: 'POST',
                                contentType: 'application/json',
                                dataType: 'json',
                                success: function() {
                                    window.location.reload();
                                }
                            });
                        }
                    }
                )
            });

        % endif

    });

    // Set up submission for addon selection form
    $('#chooseAddonsForm').on('submit', function() {

        var formData = {};
        $('#chooseAddonsForm').find('input').each(function(idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });

        $.ajax({
            url: nodeApiUrl + 'settings/addons/',
            data: JSON.stringify(formData),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                window.location.reload();
            }
        });

        return false;

    });

    // Set up submission on addon settings forms
    $('form.addon-settings').on('submit', function() {

        var $this = $(this),
            addon = $this.attr('data-addon'),
            VM = addonSettingsModels[addon],
            msgElm = $this.find('.message');

        $.ajax({
            url: nodeApiUrl + 'settings/' + addon + '/',
            data: JSON.stringify(VM.serialize().data),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json'
        }).done(function() {
            msgElm.text('Settings updated')
                .removeClass('text-danger').addClass('text-success')
                .fadeOut(100).fadeIn();
        }).fail(function() {
            msgElm.text('Error: Settings not updated')
                .removeClass('text-success').addClass('text-danger')
                .fadeOut(100).fadeIn();
        });

        return false;

    });

    ## TODO: Replace with something more fun, like the name of a famous scientist
    ## h/t @sloria
    function randomString() {
        var alphabet = 'abcdefghijkmnpqrstuvwxyz23456789',
            text = '';

        for (var i = 0; i < 5; i++)
            text += alphabet.charAt(Math.floor(Math.random() * alphabet.length));

        return text;
    }

    $('#delete-node').on('click', function() {
        var key = randomString();
        bootbox.prompt(
            '<div>Delete this ${node["category"]} and all non-project children? This is IRREVERSIBLE.</div>' +
                '<p style="font-weight: normal; font-size: medium; line-height: normal;">If you want to continue, type <strong>' + key + '</strong> and click OK.</p>',
            function(result) {
                if (result === key) {
                    window.location.href = '${node["url"]}remove/';
                }
            }
        )
    });
</script>
</%def>
