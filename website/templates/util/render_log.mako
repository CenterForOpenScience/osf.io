% if log:

    <dt><span class="date log-date">${log['date']}</span></dt>
    % if log['user']['fullname']:
        <dd><a href="/${log['user']['id']}/">${log['user']['fullname']}</a>
    % elif log['api_key']:
        <dd>${log['api_key']}
    % endif
    %if log['action'] == 'project_created':
        created <a href="${log['node']['url']}">project</a>
    %elif log['action'] == 'node_created':
        created ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'node_removed':
        ${log['node']['category']} ${log['node']['title']}
    %elif log['action'] == 'wiki_updated':
        updated wiki page <a href="${log['node']['url']}wiki/${log['params']['page']}/">${log['params']['page']}</a> to version ${log['params']['version']}
    %elif log['action'] == 'wiki_deleted':
        deleted wiki page <a href="${log['node']['url']}wiki/${log['params']['page']}/">${log['params']['page']}</a>
    %elif log['action'] == 'contributor_added':
        added
        % for contributor in log['contributors']:
            % if contributor['registered']:
                <a href="/${contributor['id']}/">${contributor['fullname']}</a>${', and ' if not loop.last else ''}
            % else:
                ${contributor['nr_name']}${', and ' if not loop.last else ''}
            % endif
        % endfor
        to ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'made_public':
        made ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
        public
    %elif log['action'] == 'made_private':
        made ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
        private
    %elif log['action'] == 'contributor_removed':
        removed
        % if log['contributor']['registered']:
            <a href="/profile/${log['contributor']['id']}/">${log['contributor']['fullname']}</a>
        % else:
            ${log['contributor']['nr_name']}
        % endif
        as a contributor from ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'tag_added':
        tagged ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
        as <a href="/tag/${log['params']['tag']}">${log['params']['tag']}</a>
    %elif log['action'] == 'tag_removed':
        removed tag <a href="/tag/${log['params']['tag']}/">${log['params']['tag']}</a> from ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'file_added':
        added file ${log['params']['path']} to ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'file_removed':
        removed file ${log['params']['path']} from ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'file_updated':
        updated file ${log['params']['path']} in ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'edit_title':
        changed the title from ${log['params']['title_original']} to <a href="${log['node']['url']}">${log['params']['title_new']}</a>
    %elif log['action'] == 'project_registered':
        <a href="/${log['params']['registration']}/">registered</a> ${log['category']}
        <a href="${log['node_url']}">${log['node_title']}</a>
        <a href="/${log['params']['registration']}/">registered</a> ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %elif log['action'] == 'node_forked':
        created fork from ${log['node']['category']}
        <a href="${log['node']['url']}">${log['node']['title']}</a>
    %endif
    </dd>

% endif
