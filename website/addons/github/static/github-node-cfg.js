var GithubConfigHelper = (function() {

    var GithubRepoModel = function(user, repo) {
        this.user = user;
        this.repo = repo;
    };

    GithubRepoModel.prototype.format = function() {
        return this.user + ' / ' + this.repo;
    };

    var GithubSettingsModel = function(config) {
        var self = this;
        self.config = config;
        self.repoModels = ko.observableArray();
        self.repoModel = ko.observable();
        self.user = ko.computed(function() {
            return self.repoModel() ? self.repoModel().user : '';
        });
        self.repo = ko.computed(function() {
            return self.repoModel() ? self.repoModel().repo : '';
        });
        self.getRepos();
    };

    GithubSettingsModel.prototype.findRepo = function(user, repo) {
        var self = this;
        var repos = self.repoModels().filter(function(item) {
            return item.user == user && item.repo == repo;
        });
        if (repos.length) {
            return repos[0];
        }
    };

    GithubSettingsModel.prototype.getRepos = function() {
        var self = this;
        if (self.config.user) {
            $.ajax({
                type: 'GET',
                url: '/api/v1/github/user/repos/',
                success: function(response) {
                    self.repoModels([]);
                    for (var i=0; i<response.length; i++) {
                        var item = response[i];
                        var repoModel = new GithubRepoModel(item.owner.login, item.name);
                        self.repoModels.push(repoModel);
                        if (self.config.repo && self.config.repo.user === item.owner.login && self.config.repo.repo === item.name) {
                            self.repoModel(repoModel);
                        }
                    }
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
                    var repoModel = new GithubRepoModel(response.user, response.repo);
                    self.repoModels.push(repoModel);
                    self.repoModel(repoModel);

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

    GithubSettingsModel.prototype.deauthorize = function() {
        var self = this;
        bootbox.confirm('Are you sure you want to remove your GitHub authorization?', function(prompt) {
            if (prompt) {
                $.ajax({
                    type: 'DELETE',
                    url: nodeApiUrl + 'github/oauth/',
                    success: function(response) {
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

    return {
        GithubSettingsModel: GithubSettingsModel
    }

})();
