<%def name="print_logs(logs, n=None)">
    <% 
        from framework import get_user
        from website.project import get_node

    %>
    <dl class="dl-horizontal activity-log">
    % for i, log in enumerate(logs):
        <% if n and i >= n:break %>
                <% 
                    tuser = log.user#get_user(log.user)
                    action = log.action
                    params = log.params
                    category = 'project' if params['project'] else 'component'
                    date = log.date
                %>
                <% if not date:
                    break
                %>
                <dt><span class="date">${date.strftime('%m/%d/%y %I:%M %p')}</span></dt>
                <dd ><a href="/profile/${tuser._primary_key}">${tuser.fullname}</a>
                %if action == 'project_created':
                    created <a href='/project/${params['project']}'>project</a>
                %elif action == 'node_created':
                    created node <a href='/project/${params['project']}/node/${params['node']}'>${get_node(params['node']).title}</a>
                %elif action == 'wiki_updated':
                    updated wiki page <a href="${get_node(params['node']).url()}/wiki/${params['page']}">${params['page']}</a> to version ${log.params['version']}
                %elif action == 'contributor_added':
                    added 
                    <% 
                        contributors = []
                        if params['contributors']:
                            for c in params['contributors']:
                                if isinstance(c, dict) and "nr_name" in c:
                                    contributors.append(c["nr_name"])
                                else:
                                    c = get_user(c)
                                    if c:
                                        contributors.append(u'<a href="/profile/{id}">{fullname}</a>'.format(id=c._primary_key, fullname=c.fullname))

                    %>
                    ${', '.join(contributors)} as contributor${'s' if len(contributors) > 1 else ''} on 
                        <% usethisnodebelowthiscode = get_node(params['node']) %>
                        node <a href=${usethisnodebelowthiscode.url()}>${usethisnodebelowthiscode.title}</a>
                %elif action == 'made_public':
                    made ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                    public
                %elif action == 'made_private':
                    made ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                    private
                %elif action == 'remove_contributor':
                    removed 
                    <% 
                        contributor = ''
                        c = params['contributor']
                        if isinstance(c, dict) and "nr_name" in c:
                            contributor = c["nr_name"]
                        else:
                            u = get_user(c)
                            if u:
                                contributor = u'<a href="/profile/{id}">{fullname}</a>'.format(id=u._primary_key, fullname=u.fullname)

                    %>
                    ${contributor} as a contributor from ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                %elif action == 'tag_added':
                    tagged ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                    as <a href="/tag/${params['tag']}">${params['tag']}</a>
                %elif action == 'tag_removed':
                    removed tag <a href="/tag/${params['tag']}">${params['tag']}</a> from ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                %elif action == 'file_added':
                    added file ${params['path']} to ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                %elif action == 'file_removed':
                    removed file ${params['path']} from ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                %elif action == 'file_updated':
                    updated file ${params['path']} in ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                %elif action == 'edit_title':
                    changed the title from ${params['title_original']} to <a href="${get_node(params['node']).url()}">${params['title_new']}</a>
                %elif action == 'project_registered':
                    <a href="/project/${params['registration']}">registered</a> ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                %elif action == 'node_forked':
                    created fork from ${category}
                    <a href="${get_node(params['node']).url()}">${get_node(params['node']).title}</a>
                %endif
            </dd>
    % endfor
    </dl>
</%def>