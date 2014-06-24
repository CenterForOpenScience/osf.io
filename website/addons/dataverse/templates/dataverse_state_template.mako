## State selector
% if authorized:
    % if has_released_files:
        <select class="dataverse-state-select">
            <option value="draft" ${"selected" if state == "draft" else ""}>Draft</option>
            <option value="released" ${"selected" if state == "released" else ""}>Released</option>
        </select>
    % else:
        [Draft]
    % endif
% else:
    [Released]
% endif