<%def name="render_addon_widget(addon_name, addon_data)">

    % if addon_data['complete'] or 'write' in user['permissions']:
        <div class="panel panel-default" name="${addon_data['short_name']}">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">${addon_data['full_name']}</h3>
                <div class="pull-right">
                    % if addon_data['has_page']:
                        <a href="${node['url']}${addon_data['short_name']}/">  <i class="fa fa-external-link"></i> </a>
                    % endif
                </div>
            </div>
            % if addon_data['complete']:
                <div class="panel-body">

                % if addon_name == 'wiki':
                    <div id="markdownRender" class="break-word scripted preview">
                        % if addon_data['wiki_content']:
                            ${addon_data['wiki_content']}
                        % else:
                            <p class="text-muted"><em>Add important information, links, or images here to describe your project.</em></p>
                        % endif
                    </div>

                    <div id="more_link">
                        % if addon_data['more']:
                            <a href="${node['url']}${addon_data['short_name']}/">Read More</a>
                        % endif
                    </div>

                    <script>
                        window.contextVars = $.extend(true, {}, window.contextVars, {
                            wikiWidget: true,
                            renderedBeforeUpdate: ${ addon_data['rendered_before_update'] | sjson, n },
                            urls: {
                                wikiContent: ${ addon_data['wiki_content_url'] | sjson, n }
                            }
                        })
                    </script>

                    <style>
                        .preview {
                            max-height: 300px;
                            overflow-y: auto;
                            padding-right: 10px;
                        }
                    </style>
                % endif

                % if addon_name == 'dataverse':
                    % if addon_data['complete']:
                        <div id="dataverseScope" class="scripted">
                            <span data-bind="if: loaded">

                                <span data-bind="if: connected">
                                    <dl class="dl-horizontal dl-dataverse" style="white-space: normal">

                                        <dt>Dataset</dt>
                                        <dd data-bind="text: dataset"></dd>

                                        <dt>Global ID</dt>
                                        <dd><a data-bind="attr: {href: datasetUrl}, text: doi"></a></dd>

                                        <dt>Dataverse</dt>
                                        <dd><a data-bind="attr: {href: dataverseUrl}"><span data-bind="text: dataverse"></span> Dataverse</a></dd>

                                        <dt>Citation</dt>
                                        <dd data-bind="text: citation"></dd>

                                    </dl>
                                </span>

                            </span>

                            <div class="help-block">
                                <p data-bind="html: message, attr: {class: messageClass}"></p>
                            </div>

                        </div>
                    % endif

                % endif

                % if addon_name == 'forward':
                    <div id="forwardScope" class="scripted">

                        <div id="forwardModal" class="p-lg" style="display: none;">

                            <div>
                                This project contains a forward to
                                <a data-bind="attr: {href: url}, text: url"></a>.
                            </div>

                            <div class="spaced-buttons m-t-md" data-bind="visible: redirecting">
                                <a class="btn btn-default" data-bind="click: cancelRedirect">Cancel</a>
                                <a class="btn btn-primary" data-bind="click: doRedirect">Redirect</a>
                            </div>

                        </div>

                        <div id="forwardWidget" data-bind="visible: url() !== null">

                            <div>
                                This project contains a forward to
                                <a data-bind="attr: {href: url}, text: linkDisplay"></a>.
                            </div>

                            <div class="spaced-buttons m-t-sm">
                                <a class="btn btn-primary" data-bind="click: doRedirect">Redirect</a>
                            </div>

                        </div>

                    </div>
                % endif

                % if addon_name == 'zotero' or addon_name == 'mendeley':
                    <script type="text/javascript">
                        window.contextVars = $.extend(true, {}, window.contextVars, {
                            ${addon_data['short_name'] | sjson , n }: {
                            folder_id: ${addon_data['list_id'] | sjson, n }
                                    }
                        });
                    </script>
                    <div class="citation-picker">
                        <input id="${addon_data['short_name']}StyleSelect" type="hidden" />
                    </div>
                    <div id="${addon_data['short_name']}Widget" class="citation-widget">
                        <div class="spinner-loading-wrapper">
                            <div class="ball-scale ball-scale-blue">
                                <div></div>
                            </div>
                            <p class="m-t-sm fg-load-message"> Loading citations...</p>
                        </div>
                    </div>
                % endif


                </div>
            % else:
                <div class='addon-config-error p-sm'>
                    ${addon_data['full_name']} add-on is not configured properly.
                    % if user['is_contributor']:
                        Configure this add-on on the <a href="${node['url']}addons/">add-ons</a> page.
                    % endif
                </div>

            % endif
        </div>
    % endif

</%def>
<%inherit file="../project/addon/widget.mako"/>
