% for contributor in contributors:
    <span class="contributor">
        <a href="/profile/${contributor['id']}/"
            % if user_can_edit:
                class="user-quickedit" data-userid="${contributor['id']}" data-fullname="${contributor['fullname']}"
            % endif
                >${contributor['fullname']}</a>${', ' if not loop.last else ''}
    </span>
% endfor

% if user_can_edit:
    | <a data-target="#addContributors" data-toggle="modal">add</a>
% endif
