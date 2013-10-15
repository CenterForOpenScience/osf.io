<div class="list-group">

        <h4 class="list-group-item"><a href="/project/${node_id}/wiki/home">Project</a></h4>

        % for k in pages_current:
            % if not k == 'home':
                    <a href="/project/${node_id}/wiki/${k}">${k}</a>
            % endif
        % endfor

        % for child in toc:
                <h4 class="list-group-item">
                    <a href="/project/${node_id}/node/${child['id']}/wiki/home">${child['title']} (${child['category']})</a>
                </h4>
            % for k in child['pages']:
                % if k != 'home':
                        <a class="list-group-item" href="/project/${node_id}/node/${child['id']}/wiki/${k}">${k}</a>
                % endif
            % endfor

        % endfor

    </ul>

</div>
