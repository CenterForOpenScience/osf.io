<div class="well" style="padding: 8px 0;">

    <ul class="nav nav-list">

        <li class="nav-header">
            <a href="/project/${node_id}/wiki/home">Project</a>
        </li>

        % for k in pages_current:
            % if not k == 'home':
                <li>
                    <a href="/project/${node_id}/wiki/${k}">${k}</a>
                </li>
            % endif
        % endfor

        % for child in toc:

            <li class="nav-header">
                <a href="/project/${node_id}/node/${child['id']}/wiki/home">${child['title']} (${child['category']})</a>
            </li>
            % for k in child['pages']:
                % if k != 'home':
                    <li>
                        <a href="/project/${node_id}/node/${child['id']}/wiki/${k}">${k}</a>
                    </li>
                % endif
            % endfor

        % endfor

    </ul>

</div>