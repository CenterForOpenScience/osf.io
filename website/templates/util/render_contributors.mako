% for contributor in contributors:
    <span data-pk="${contributor['id']}"
            class="contributor
                ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}
                ${'contributor-self' if user['id'] == contributor['id'] else ''}">
        % if contributor['registered']:
        <a href="/${contributor['id']}/">${contributor['fullname']}</a>
        % else:
        <span>${contributor['fullname']}</span>
        %endif
    </span>
    ${'' if loop.last else '|'}
% endfor
