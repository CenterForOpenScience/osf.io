## State selector
% if authorized:
    % if has_published_files:
        <select class="dataverse-state-select">
            <option value="draft" ${"selected" if state == "draft" else ""}>Draft</option>
            <option value="published" ${"selected" if state == "published" else ""}>Published</option>
        </select>
    % else:
        [Draft]
    % endif
% else:
    [Published]
% endif