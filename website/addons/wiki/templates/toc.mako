<div class="osf-sidenav hidden-print" role="complementary">

    <ul class="nav bs-sidenav">

        <h4 style="margin-left: 10px;">Project Wiki Pages</h4>

        % for k in pages_current:
            <li>
                <a href="/${node['id']}/wiki/${k}">${k}</a>
            </li>
        % endfor

        % if category == 'project':
            <hr />
            <h4 style="margin-left: 10px;">Component Wiki Pages</h4>

            % for child in toc:
                <li class="nav-header">

                    <a href="${child['url']}">
                        % if child['is_pointer']:
                            <i class="icon-hand-right"></i>
                        % endif

                        ${child['title']}
                        % if child['category']:
                            (${child['category']})
                        % endif
                    </a>

                    <ul style="list-style-type: none;">
                        % for k in child['pages']:
                            % if k != 'home':
                                <li class="">
                                    <a href="/${node['id']}/node/${child['id']}/wiki/${k}">${k}</a>

                                </li>
                            % endif
                        % endfor
                    </ul>

                </li>
            % endfor
        % endif

    </ul>

</div>
