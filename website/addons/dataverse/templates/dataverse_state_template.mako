 <i id="dataverseGetCitation" class="icon-info-sign"></i>
% if authorized:
    % if has_released_files:
        <select class="dataverse-state-select">
            <option value="draft" ${"selected" if state == "draft" else ""}>Draft</option>
            <option value="released" ${"selected" if state == "released" else ""}>Released</option>
        </select>
    % else:
        [Draft]
    % endif
    % if state == "draft" and file_page:
        <a id="dataverseReleaseStudy">Release Study</a>
    % endif
% else:
    [Released]
% endif