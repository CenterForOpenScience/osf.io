<div id="projectScope">
    <header class="subhead" id="overview">

        <div id="title" class="row">
            <h2 class="node-title">
                <span id="nodeTitle" class="overflow">${ node['title'] }</span>
            </h2>
        </div>

        <div id="contributors" class="row" style="line-height:25px">
            <div class="col-sm-12">
                Contributors:
                % if node['anonymous'] and not node['is_public']:
                    <ol>Anonymous Contributors</ol>
                % else:
                    <ol>
                        <div mod-meta='{
                            "tpl": "util/render_contributors.mako",
                            "uri": "${ node["api_url"] }get_contributors/",
                            "replace": true
                        }'></div>
                    </ol>
                % endif
                % if node['is_fork']:
                    <br />Forked from <a class="node-forked-from" href="/${node['forked_from_id']}/">${node['forked_from_display_absolute_url']}</a> on
                    <span data-bind="text: dateForked.local, tooltip: {title: dateForked.utc}"></span>
                % endif
                % if node['is_registration'] and node['registered_meta']:
                    <br />Registration Supplement:
                    % for meta in node['registered_meta']:
                        <a href="${node['url']}register/${meta['name_no_ext']}">${meta['name_clean']}</a>
                    % endfor
                % endif
                <br />
                Date Created: ${ node['date_created'] }
                | Last Updated: ${ node['date_modified'] }
                % if parent_node['id']:
                    <br />Category: <span class="node-category">${ node['category'] }</span>
                % elif node['description'] or 'write' in user['permissions']:
                    <br /><span id="description">Description:</span> <span id="nodeDescriptionEditable" class="node-description overflow" data-type="textarea">${ node['description'] }</span>
                % endif
            </div>
        </div>

        <div id="justification" class="row">
            <div class="col-sm-6">
                <div id="justificationWidget" class="addon-widget-container">
                    <div class="addon-widget" name="justification">
                        <div class="addon-widget-header clearfix">
                            <h4>Justification for Retraction</h4>
                        </div>
                        <div class="addon-widget-body">
                            % if node['retracted_justification'] is None:
                                <em>No justification provided during retraction.</em>
                            % else:
                                <em>${ node['retracted_justification'] }</em>
                            % endif
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </header>
</div>
