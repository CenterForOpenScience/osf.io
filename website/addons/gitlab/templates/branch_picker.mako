% if len(branches) > 1:
    <select class="gitlab-branch-select">
        % for each in branches:
            <option value="${each}" ${"selected" if each == branch else ""}>${each}</option>
        % endfor
    </select>
% else:
    <span>${branch}</span>
% endif
