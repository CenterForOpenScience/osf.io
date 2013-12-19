<div class="osf-sidenav hidden-print" role="complementary">

    <ul class="nav bs-sidenav">

        <h4 style="margin-left: 10px;">Project Wiki Pages</h4>

        % for k in pages_current:
            <li>
                <a
                  % if node['link']:
                    href="/${node['id']}/wiki/${k}/?key=${node['link']}"
                  % else:
                    href="/${node['id']}/wiki/${k}/"
                  % endif
                        >${k}</a>
            </li>
        % endfor

        % if category == 'project':
            <hr />
            <h4 style="margin-left: 10px;">Component Wiki Pages</h4>

            % for child in toc:
                <li class="nav-header">
                    % if child['link']:

                        <a href="/${node['id']}/node/${child['id']}/wiki/home/?key=${child['link']}">${child['title']} (${child['category']})</a>
                        <ul style="list-style-type: none;">
                            % for k in child['pages']:
                                % if k != 'home':
                                    <li class="">
                                        <a href="/${node_id}/node/${child['id']}/wiki/${k}/?key=${child['link']}">${k}</a>
                                    </li>
                                % endif
                            % endfor
                        </ul>
                    % else:
                        <a href="/${node['id']}/node/${child['id']}/wiki/home/">${child['title']} (${child['category']})</a>
                        <ul style="list-style-type: none;">
                            % for k in child['pages']:
                                % if k != 'home':
                                    <li class="">
                                        <a href="/${node_id}/node/${child['id']}/wiki/${k}/">${k}</a>
                                    </li>
                                % endif
                            % endfor
                        </ul>
                    % endif
                </li>
            % endfor

        % endif

    </ul>

</div>
