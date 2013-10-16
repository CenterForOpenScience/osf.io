% if log:

    <dt><span class="date">${log['date']}</span></dt>
    % if log['user_fullname']:
        <dd><a href="/profile/${log['user_id']}/">${log['user_fullname']}</a>
    % elif log['api_key']:
        <dd>${log['api_key']}
    % endif
    %if log['action'] == 'project_created':
        created <a href="${log['project_url']}">project</a>
    %elif log['action'] == 'node_created':
        created ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %elif log['action'] == 'wiki_updated':
        updated wiki page <a href="${log['node_url']}wiki/${log['params']['page']}/">${log['params']['page']}</a> to version ${log['params']['version']}
    %elif log['action'] == 'contributor_added':
        added
        % for contributor in log['contributors']:
            % if contributor['registered']:
                <a href="/profile/${contributor['id']}/">${contributor['fullname']}</a>${', ' if not loop.last else ''}
            % else:
                ${contributor['nr_name']}${', ' if not loop.last else ''}
            % endif
        % endfor
        to ${log['category']}
        <a href=${log['node_url']}>${log['node_title']}</a>
    %elif log['action'] == 'made_public':
        made ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
        public
    %elif log['action'] == 'made_private':
        made ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
        private
    %elif log['action'] == 'remove_contributor':
        removed
        % if log['contributor']['registered']:
            <a href="/profile/${log['contributor']['id']}/">${log['contributor']['fullname']}</a>
        % else:
            ${log['contributor']['nr_name']}
        % endif
        as a contributor from ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %elif log['action'] == 'tag_added':
        tagged ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
        as <a href="/tag/${log['params']['tag']}">${log['params']['tag']}</a>
    %elif log['action'] == 'tag_removed':
        removed tag <a href="/tag/${log['params']['tag']}/">${log['params']['tag']}</a> from ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %elif log['action'] == 'file_added':
        added file ${log['params']['path']} to ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %elif log['action'] == 'file_removed':
        removed file ${log['params']['path']} from ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %elif log['action'] == 'file_updated':
        updated file ${log['params']['path']} in ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %elif log['action'] == 'edit_title':
        changed the title from ${log['params']['title_original']} to <a href="${log['node_url']}">${log['params']['title_new']}</a>
    %elif log['action'] == 'project_registered':
        <a href="/project/${log['params']['registration']}/">registered</a> ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %elif log['action'] == 'node_forked':
        created fork from ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
    %endif
    </dd>

% endif
