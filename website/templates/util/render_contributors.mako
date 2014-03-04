% for contributor in contributors:
    <span data-pk="${contributor['id']}"
        class="contributor ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}">
        % if contributor['registered']:
            <a href="/${contributor['id']}/"
                % if user['can_edit']:
                    class="user-quickedit"
                    data-userid="${contributor['id']}" data-fullname="${contributor['fullname']}"
                % endif
                >${contributor['fullname']}</a>${', ' if not loop.last else ''}
        % else:
            <span
                % if user['can_edit']:
                    class="user-quickedit"
                    data-userid="${contributor['id']}" data-fullname="${contributor['fullname']}"
                % endif
                >${contributor['fullname']}</span>${', ' if not loop.last else ''}
        % endif
    </span>
% endfor

% if user['can_edit']:
    | <a href="#addContributors" data-toggle="modal">add</a>
% endif
