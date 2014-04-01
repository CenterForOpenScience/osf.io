<%inherit file="../../project/addon/node_settings.mako" />


<script type="text/javascript" src="/static/addons/figshare/figshare-node-cfg.js"></script>

% if node_has_auth:

    <input type="hidden" id="figshareId" name="figshare_value" value="${figshare_type + '_' + figshare_id}">
    <input type="hidden" id="figshareTitle" name="figshare_title" value="${figshare_title}">

    <div class="well well-sm">
        <span>Authorized by <a href="${owner_url}">${authorized_user}</a></span>
        % if user_has_auth:
            <a id="figshareDelKey" class="text-danger pull-right" style="cursor: pointer">Deauthorize</a>
        % endif
    </div>


    <div class="row">
            <div class="col-md-6">
                <select id="figshareSelectProject" class="form-control" ${'' if is_owner and not is_registration else 'disabled'}>
                    <option>-----</option>
                    %if is_owner:
                        ##TODO Better naming scheme and remove the spilt?
                        % for project in figshare_options:
                            <option value="${project['value']}" ${'selected' if project['label'] == figshare_title else ''}>
                            ${'{0}:{1}'.format(project['label'] or 'Unnamed', project['value'].split('_')[1])}
                            ${' (project)' if 'project' in project['value'] else ''}
                            </option>
                        % endfor
                    %else:
                        <option value="${figshare_type + '_' + figshare_id}" selected>
                            ${'{0}:{1}'.format(figshare_title or 'Unnamed', figshare_id)}
                            </option>>
                    %endif
                </select>
            </div>

        % if is_owner and not is_registration:
            <div class="col-md-6">
                <a id="figshareCreateFileSet" class="btn btn-default">Create File Set</a>
            </div>
        % endif


    </div>



%else:
    <a id="figshareAddKey" class="btn btn-primary">
        %if user_has_auth:
            Authorize: Import Token from Profile
        %else:
            Authorize: Create Access Token
        %endif
    </a>
% endif

<%def name="submit_btn()">
    % if node_has_auth and is_owner and user_has_auth:
        <br />
        ${parent.submit_btn()}
    % endif
</%def>
