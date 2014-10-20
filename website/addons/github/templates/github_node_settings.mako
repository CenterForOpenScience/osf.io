##<script type="text/javascript" src="/static/addons/github/github-node-cfg.js"></script>

##<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <div id="githubScope" class="scripted">
        <h4 class="addon-title">
            GitHub
            <small class="authorized-by">
                <span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr.href: urls().owner">
                    {{ownerName}}
                </a>
                % if not is_registration:
                    <a data-bind="click: deauthorize"
                        class="text-danger pull-right addon-auth">Deauthorize</a>
                % endif
                </span>

                 <!-- Import Access Token Button -->
                <span data-bind="if: showImport">
                    <a data-bind="click: importAuth" href="#" class="text-primary pull-right addon-auth">
                        Import Access Token
                    </a>
                </span>

                <!-- Oauth Start Button -->
                <span data-bind="if: showTokenCreateButton">
                    <a data-bind="attr.href: urls().auth" class="text-primary pull-right addon-auth">
                        Create Access Token
                    </a>
                </span>

            </small>
        </h4>
    </div>




<%def name="on_submit()">
##    <script type="text/javascript">
##        $(document).ready(function() {
##            $('#addonSettings${addon_short_name.capitalize()}').on('submit', AddonHelper.onSubmitSettings);
##        });
##    </script>
</%def>

<script>
    $script.ready('zeroclipboard', function() {
        ZeroClipboard.config({moviePath: '/static/vendor/bower_components/zeroclipboard/ZeroClipboard.swf'})
    });
    $script(['/static/addons/github/githubNodeConfig.js']);
    $script.ready('githubNodeConfig', function() {

        var url = '${node["api_url"] + "github/config/"}';
        console.log(url);
        console.log(githubScope);
        var github = new GithubNodeConfig('#githubScope', url);
        console.log(github);
    });
</script>
