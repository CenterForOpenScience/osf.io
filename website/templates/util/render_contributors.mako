% for contributor in contributors:
    <li data-pk="${contributor['id']}"
            class="contributor
                ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}
                ${'contributor-self' if user['id'] == contributor['id'] else ''}">
        <%
            condensed = contributor['fullname']
            if len(condensed) >= 50:
                condensed = condensed[:23] + "..." + condensed[-23:]
        %>
        % if contributor['registered']:
            <a class='user-profile' href="/${contributor['id']}/">${condensed}</a></li>
        % else:
        <span>${condensed}</span></li>

        %endif
% endfor

