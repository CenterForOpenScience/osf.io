<%inherit file="project/addon/node_settings.mako" />

<!-- Authorization -->
<div>
    <div class="alert alert-danger alert-dismissable">
    <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        Authorizing this GitHub add-on will grant all contributors on this ${node['category']}
        permission to upload, modify, and delete files on the associated GitHub repo.
    </div>
    <div class="alert alert-danger alert-dismissable">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        If one of your collaborators removes you from this ${node['category']},
        your authorization for GitHub will automatically be revoked.
    </div>
    % if authorized_user_id:
        <a id="githubDelKey" class="btn btn-danger">Unauthorize: Detach Access Token</a>
        <div style="padding-top: 10px">
            Authorized by OSF user
            <a href="${domain}/${authorized_user_id}" target="_blank">
                ${authorized_user_name}
            </a>
            on behalf of GitHub user
            <a href="https://github.com/${authorized_github_user}" target="_blank">
                ${authorized_github_user}
            </a>
        </div>
    % else:
        <div>
            Adding a GitHub access token allows you and your collaborators to
            update and delete files on your linked repository, and view its files
            if this repository is private. If you do not add an access token, you
            will be able to view and download files within the repository if it
            is public.
        </div>
        <br />
        <a id="githubAddKey" class="btn btn-primary">
            % if user_has_authorization:
                Authorize: Import Access Token from Profile
            % else:
                Authorize: Create Access Token
            % endif
        </a>
    % endif
</div>

<br />

<div class="form-group">
    <label for="githubUser">GitHub User</label>
    <input class="form-control" id="githubUser" name="github_user" value="${github_user}" ${'disabled' if disabled else ''} />
</div>
<div class="form-group">
    <label for="githubRepo">GitHub Repo</label>
    <input class="form-control" id="githubRepo" name="github_repo" value="${github_repo}" ${'disabled' if disabled else ''} />
</div>

<script type="text/javascript">

    $(document).ready(function() {

        $('#githubAddKey').on('click', function() {
            % if authorized_user_id:
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'github/user_auth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                window.location.href = nodeApiUrl + 'github/oauth/';
            % endif
        });

        $('#githubDelKey').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to detach your GitHub access key? This will ' +
                    'revoke the ability to modify and upload files to GitHub. If ' +
                    'the associated repo is private, this will also disable viewing ' +
                    'and downloading files from GitHub. This will not remove your ' +
                    'GitHub authorization from your <a href="/settings/">user settings</a> ' +
                    'page.',
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
    });

</script>

<%def name="submit_btn()">
    % if show_submit:
        ${parent.submit_btn()}
    % endif
</%def>

<%def name="on_submit()">
    % if show_submit:
        ${parent.on_submit()}
    % endif
</%def>
