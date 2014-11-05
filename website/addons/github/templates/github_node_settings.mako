
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


            <div class="github-settings"  data-bind = "if:showSettings">
                <form id=addonSettings  data-bind = submit:submitSettings >
                    <div class="row">
                        <div class="col-md-6">
                            <select class="form-control col-md-6" data-bind = "options:displayRepos, value:SelectedRepository, optionsCaption:'Select your Repository'"></select>
                        </div>
                        <div class="col-md-6" id="displayRepositories">
                            <span> or </span>
                            <button data-bind="click:createRepo" class="btn btn-link">Create Repo</button>
                        </div>
                    </div>
                    <div class="row" style="padding-top: 20px" data-bind="visible:SelectedRepository">
                        <h4 class="col-md-8">Connect "<span data-bind="text:SelectedRepository()"></span>"?</h4>
                        <div class="pull-right col-md-4">
                            <button class="btn btn-default" data-bind="click:cancel">Cancel</button>
                            <input type="submit" class="btn btn-primary" value="Submit">
                        </div>
                    </div>
                </form>
            </div>

        <div class="addon-settings-message" style="padding-top: 10px;" data-bind ="text:displayMessage"></div>

    </div><!-- End of githubScope-->







<script>
    $script.ready('zeroclipboard', function() {
        ZeroClipboard.config({moviePath: '/static/vendor/bower_components/zeroclipboard/ZeroClipboard.swf'})
    });
    $script(['/static/addons/github/githubNodeConfig.js']);
    $script.ready('githubNodeConfig', function() {

        var url = '${node["api_url"] + "github/config/"}';
        var submitUrl = '${node["api_url"] + "github/settings/"}'
        var github = new GithubNodeConfig('#githubScope', url, submitUrl);
        console.log(github);
    });
</script>
