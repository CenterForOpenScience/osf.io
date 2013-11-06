<div class="osf-sidebar hidden-print" role="complementary">
    <ul class="nav bs-sidenav">

        <li><a href="/project/${node_id}/wiki/home">Project</a></li>

        % for k in pages_current:
            % if not k == 'home':
                    <a href="/project/${node_id}/wiki/${k}">${k}</a>
            % endif
        % endfor

        % for child in toc:
                <li>
                    <a href="/project/${node_id}/node/${child['id']}/wiki/home">${child['title']} (${child['category']})</a>
                </li>
            % for k in child['pages']:
                % if k != 'home':
                        <a class="list-group-item" href="/project/${node_id}/node/${child['id']}/wiki/${k}">${k}</a>
                % endif
            % endfor

        % endfor

    </ul>

</div>
