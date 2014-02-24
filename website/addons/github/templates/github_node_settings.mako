<%inherit file="project/addon/node_settings.mako" />

<div>

    <div data-bind="if: config.repo">

        <input type="hidden" id="githubUser" name="github_user" data-bind="value: user" />
        <input type="hidden" id="githubRepo" name="github_repo" data-bind="value: repo" />

        <div class="well well-sm">
            Authorized by
            <a data-bind="text: config.user.osfUser, attr: {href: config.user.osfUrl}"></a>
            on behalf of GitHub user
            <a target="_blank" data-bind="text: config.user.githubUser, attr: {href: config.user.githubUrl}"></a>
        </div>

        <div class="row">

            <div class="col-md-6">
                <select class="form-control" data-bind="options: repoModels, optionsText: function(item) {return item.format()}, value: repoModel">
                </select>
            </div>

            <div class="col-md-6">
                <a class="btn btn-default" data-bind="visible: config.user.owner, click: newRepo">Create Repo</a>
            </div>

        </div>

    </div>

    <div data-bind="ifnot: config.repo">

        <a class="btn btn-primary" data-bind="click: addAuth">
            <div data-bind="if: config.hasAuth">
                Authorize: Import Access Token from Profile
            </div>
            <div data-bind="ifnot: config.hasAuth">
                Authorize: Create Access Token
            </div>
        </a>

    </div>

    <br />

</div>

<script type="text/javascript" src="/addons/static/github/github-node-cfg.js"></script>
<script type="text/javascript">

    var githubConfig = ${github_config};
    $(document).ready(function() {
        var githubSettingsModel = new GithubConfigHelper.GithubSettingsModel(githubConfig);
        ko.applyBindings(githubSettingsModel, document.getElementById('addonSettingsGithub'));
    });

</script>
