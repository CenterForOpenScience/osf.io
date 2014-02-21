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

        <div class="btn-group">
            <button type="button" class="btn btn-default" data-bind="disable: !config.user.owner">
                <span id="githubRepoLabel" data-bind="text: repoLabel"></span>
            </button>
            <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" data-bind="disable: !config.user.owner">
                <span class="caret"></span>
            </button>
            <ul id="githubDropdown" class="dropdown-menu pull-right dropdown-scroll" role="menu" data-bind="foreach: repoModels">
                <li role="presentation">
                    <a href="#" data-bind="text: $data.format(), click: $root.selectRepo.bind($root)"></a>
                </li>
            </ul>
        </div>

        <br /><br />

        <div>
            <a class="btn btn-success" data-bind="visible: config.user.owner, click: newRepo">Create Repo</a>
            <a class="btn btn-danger" data-bind="click: deauthorize">Deauthorize</a>
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

</div>

<script type="text/javascript">

    var githubConfig = ${github_config};

    var GithubRepoModel = function(data) {
        this.data = data;
    };
    GithubRepoModel.prototype.format = function() {
        return this.data.owner.login + ' / ' + this.data.name;
    };

    var GithubSettingsModel = function($elm, config) {
        var self = this;
        this.$elm = $elm;
        self.config = config;
        self.user = ko.observable();
        self.repo = ko.observable();
        self.repoModels = ko.observableArray();
        self.repoModel = ko.observable();
        if (config.repo) {
            self.user(config.repo.user);
            self.repo(config.repo.repo);
        }
        self.repoLabel = ko.computed(function() {
            var repoModel = self.repoModel();
            if (repoModel) {
                return repoModel.format();
            } else if (self.user() && self.repo()) {
                return self.user() + ' / ' + self.repo();
            } else {
                return 'Select a repository';
            }
        });
        self.getRepos();
    };

    GithubSettingsModel.prototype.getRepos = function() {
        var self = this;
        if (self.config.user) {
            $.ajax({
                type: 'GET',
                url: '/api/v1/github/users/' + self.config.user.githubUser + '/repos/',
                success: function(response) {
                    self.repoModels(
                        response.map(function(item) {
                            return new GithubRepoModel(item)}
                        )
                    );
                }
            });
        }
    };

    GithubSettingsModel.prototype.newRepo = function() {
        var self = this;
        bootbox.prompt('Name your new repo', function(repoName) {
            $.ajax({
                type: 'POST',
                url: '/api/v1/github/repo/create/',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({name: repoName}),
                success: function(response) {
                    self.user(response.user);
                    self.repo(response.repo);
                    self.submit();
                },
                error: function() {
                    $('#addonSettingsGithub').find('.addon-settings-message')
                        .text('Could not create repository')
                        .removeClass('text-success').addClass('text-danger')
                        .fadeOut(100).fadeIn();
                }
            });
        });
    };

    GithubSettingsModel.prototype.selectRepo = function(repoModel) {

        this.repoModel(repoModel);
        this.repo(repoModel.data.name);
        this.user(repoModel.data.owner.login);

        // Hide dropdown
        this.$elm.find('.dropdown-toggle')
            .dropdown('toggle');

        this.submit();

    };

    GithubSettingsModel.prototype.submit = function() {
        this.$elm.submit();
    };

    GithubSettingsModel.prototype.deauthorize = function() {
        var self = this;
        bootbox.confirm('Are you sure you want to remove your GitHub authorization?', function(prompt) {
            if (prompt) {
                $.ajax({
                    type: 'DELETE',
                    url: nodeApiUrl + 'github/oauth/',
                    success: function(response) {
                        // TODO: Single-page-ify
                        window.location.reload();
                    }
                });
            }
        });
    };

    GithubSettingsModel.prototype.addAuth = function() {

        var self = this;
        if (self.config.authUser) {
            $.ajax({
                type: 'POST',
                url: nodeApiUrl + 'github/user_auth/',
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    window.location.reload();
                }
            });
        } else {
            window.location.href = nodeApiUrl + 'github/oauth/';
        }
    };

    $(document).ready(function() {
        var githubSettingsModel = new GithubSettingsModel($('#addonSettingsGithub'), githubConfig);
        ko.applyBindings(githubSettingsModel, document.getElementById('addonSettingsGithub'));
    });

</script>

<%def name="submit_btn()"></%def>

<%def name="on_submit()">
    ${parent.on_submit()}
</%def>
