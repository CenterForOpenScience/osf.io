% for contributor in contributors:
    <span data-pk="${contributor['id']}"
        class="contributor ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}">
        % if contributor['registered']:
            <a href="/${contributor['id']}/"
                % if user['can_edit']:
                    class="user-quickedit"
                    data-userid="${contributor['id']}" data-fullname="${contributor['fullname']}"
                % endif
                >${contributor['fullname']}</a>
        % else:
            <span
                % if user['can_edit']:
                    class="user-quickedit"
                    data-userid="${contributor['id']}" data-fullname="${contributor['fullname']}"
                % endif
                >${contributor['fullname']}</span>
        % endif
    </span>
    ${', ' if not loop.last else ''}
% endfor

% if user['can_edit']:
    | <a href="#addContributors" data-toggle="modal">add</a>
% endif
