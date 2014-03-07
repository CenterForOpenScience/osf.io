<%inherit file="project/addon/node_settings.mako" />


<script type="text/javascript" src="/addons/static/figshare/figshare-node-cfg.js"></script>

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
                <select id="figshareSelectProject" class="form-control" ${'' if is_owner else 'disabled'}>
                    <option>-----</option>
                    %if is_owner:
                        % for project in figshare_options:
                            <option value="${project['value']}" ${'selected' if project['label'] == figshare_title else ''}>${project['label']}</option>
                        % endfor
                    %else:
                        <option value="${figshare_type + '_' + figshare_id}" selected>${figshare_title}</option>>
                    %endif
                </select>
            </div>
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
