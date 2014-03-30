<%inherit file="../../project/addon/node_settings.mako" />

<script type="text/javascript" src="/static/addons/github/github-node-cfg.js"></script>

% if node_has_auth:

    <input type="hidden" id="githubUser" name="github_user" value="${github_user}" />
    <input type="hidden" id="githubRepo" name="github_repo" value="${github_repo}" />

    <div class="well well-sm">
        Authorized by <a href="${auth_osf_url}">${auth_osf_name}</a>
        on behalf of GitHub user <a target="_blank" href="${github_user_url}">${github_user_name}</a>
        % if user_has_auth:
            <a id="githubRemoveToken" class="text-danger pull-right" style="cursor: pointer">Deauthorize</a>
        % endif
    </div>

    <div class="row">

        <div class="col-md-6">
            <select id="githubSelectRepo" class="form-control" ${'disabled' if not is_owner or is_registration else ''}>
                <option>-----</option>
                    % if is_owner:
                        % for repo_name in repo_names:
                            <option value="${repo_name}" ${'selected' if repo_name == github_repo_full_name else ''}>${repo_name}</option>
                        % endfor
                    % else:
                        <option selected>${github_repo_full_name}</option>
                    % endif
            </select>
        </div>

        % if is_owner and not is_registration:
            <div class="col-md-6">
                <a id="githubCreateRepo" class="btn btn-default">Create Repo</a>
            </div>
        % endif

    </div>

    <br />

% elif user_has_auth:

    <a id="githubImportToken" class="btn btn-primary">
        Authorize: Import Access Token from Profile
    </a>

% else:

    <a id="githubCreateToken" class="btn btn-primary">
        Authorize: Create Access Token
    </a>

% endif

<%def name="submit_btn()">
    % if node_has_auth:
        ${parent.submit_btn()}
    % endif
</%def>
