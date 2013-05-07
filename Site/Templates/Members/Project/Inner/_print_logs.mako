<%def name="print_logs(logs, n=None)">
    <% 
        from Framework import getUser 
        from Site.Project import getNode

    %>
    <dl class="dl-horizontal">
    % for i, log in enumerate(logs):
        <% if n and i >= n:break %>
                <% 
                    tuser = getUser(log['user']) 
                    action = log['action']
                    params = log['params']
                    date = log['date']
                %>
                <% if not date:
                    break
                %>
                <dt><span class="date">${date.strftime('%m/%d/%y %I:%M %p')}</span></dt>
                <dd ><a href="/profile/${tuser.id}">${tuser.fullname}</a> 
                %if action == 'project_created':
                    created <a href='/project/${params['project']}'>project</a>
                %elif action == 'node_created':
                    created node <a href='/project/${params['project']}/node/${params['node']}'>${getNode(params['node']).title}</a>
                %elif action == 'wiki_updated':
                    %if params['project']:
                    updated wiki page <a href="/project/${params['project']}/node/${params['node']}/wiki/${params['page']}">${params['page']}</a> to version ${log.params['version']}
                    %else:
                    updated wiki page <a href="/project/${params['node']}/wiki/${params['page']}">${params['page']}</a> to version ${params['version']}
                    %endif
                %elif action == 'contributor_added':
                    added 
                    <% 
                        contributors = []
                        if params['contributors']:
                            for c in params['contributors']:
                                if isinstance(c, dict) and "nr_name" in c:
                                    contributors.append(c["nr_name"])
                                else:
                                    c = getUser(c)
                                    if c:
                                        contributors.append('<a href="/profile/{id}">{fullname}</a>'.format(id=c.id, fullname=c.fullname))

                    %>
                    ${', '.join(contributors)} as contributor${'s' if len(contributors) > 1 else ''} on 
                        <% usethisnodebelowthiscode = getNode(params['node']) %>
                        node <a href=${usethisnodebelowthiscode.url()}>${usethisnodebelowthiscode.title}</a>
                %elif action == 'made_public':
                    made
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                    public
                %elif action == 'made_private':
                    made
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                    private
                %elif action == 'remove_contributor':
                    removed 
                    <% 
                        contributor = ''
                        c = params['contributor']
                        if isinstance(c, dict) and "nr_name" in c:
                            contributor = c["nr_name"]
                        else:
                            u = getUser(c)
                            if u:
                                contributor = '<a href="/profile/{id}">{fullname}</a>'.format(id=u.id, fullname=u.fullname)

                    %>
                    ${contributor} as a contributor from
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                %elif action == 'tag_added':
                    tagged
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                    as <a href="/tag/${params['tag']}">${params['tag']}</a>
                %elif action == 'tag_removed':
                    removed tag <a href="/tag/${params['tag']}">${params['tag']}</a> from
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                %elif action == 'file_added':
                    added file ${params['path']} to
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                %elif action == 'file_updated':
                    updated file ${params['path']} in
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                %elif action == 'edit_title':
                    changed the title from ${params['title_original']} to <a href="${getNode(params['node']).url()}">${params['title_new']}</a>
                %elif action == 'project_registered':
                    <a href="/project/${params['registration']}">registered</a> 
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                %elif action == 'node_forked':
                    created fork from
                    %if params['project']:
                        node <a href="/project/${params['project']}/node/${params['node']}">${getNode(params['node']).title}</a>
                    %else:
                        project <a href="/project/${params['node']}">${getNode(params['node']).title}</a>
                    %endif
                %endif
            </dd>
    % endfor
    </dl>
</%def>