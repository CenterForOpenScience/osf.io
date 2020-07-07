<%def name="render_addon_widget(addon_name, addon_data)">

    % if addon_data['complete'] or permissions.WRITE in user['permissions']:
        <div class="panel panel-default" name="${addon_data['short_name']}">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">${addon_data['full_name']}</h3>
                <div class="pull-right">
                    % if addon_data['has_page']:
                        <a href="${node['url']}${addon_data['short_name']}"><i class="fa fa-external-link"></i></a>
                    % endif
                    % if 'can_expand' in addon_data and addon_data['can_expand']:
                        <button class="btn btn-link project-toggle"><i class="fa fa-angle-down"></i></button>
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
                            <p class="text-muted"><em>${_("Add important information, links, or images here to describe your project.")}</em></p>
                        % endif
                    </div>

                    <div id="more_link">
                        % if addon_data['more']:
                            <a href="${node['url']}${addon_data['short_name']}/">${_("Read More")}</a>
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

                                        <dt>${_("Dataset")}</dt>
                                        <dd data-bind="text: dataset"></dd>

                                        <dt>${_("Global ID")}</dt>
                                        <dd><a data-bind="attr: {href: datasetUrl}, text: doi"></a></dd>

                                        <dt>${_("Dataverse")}</dt>
                                        <dd><a data-bind="attr: {href: dataverseUrl}"><span data-bind="text: dataverse"></span> ${_("Dataverse")}</a></dd>

                                        <dt>${_("Citation")}</dt>
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
                                ${_('This project contains a forward to\
                                <a %(textUrl)s></a>.') % dict(textUrl='data-bind="attr: {href: url}, text: url"') | n}
                            </div>

                            <div class="spaced-buttons m-t-md" data-bind="visible: redirecting">
                                <a class="btn btn-default" data-bind="click: cancelRedirect">${_("Cancel")}</a>
                                <a class="btn btn-primary" data-bind="click: doRedirect">${_("Redirect")}</a>
                            </div>

                        </div>

                        <div id="forwardWidget" data-bind="visible: url() !== null">

                            <div>
                                ${_('This project contains a forward to\
                                <a %(textLinkDisplay)s></a>.') % dict(textLinkDisplay='data-bind="attr: {href: url}, text: linkDisplay"') | n}
                            </div>

                            <div class="spaced-buttons m-t-sm">
                                <a class="btn btn-primary" data-bind="click: doRedirect">${_("Redirect")}</a>
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
                            <p class="m-t-sm fg-load-message"> ${_("Loading citations...")}</p>
                        </div>
                    </div>
                % endif

                % if addon_name == 'jupyterhub':
                    <div id="jupyterhubLinks" class="scripted">
                      <!-- ko if: loading -->
                      <div>${_("Loading")}</div>
                      <!-- /ko -->
                      <!-- ko if: loadFailed -->
                      <div class="text-danger">${_("Error occurred")}</div>
                      <!-- /ko -->
                      <!-- ko if: loadCompleted -->
                        <!-- ko if: availableServices().length > 0 -->
                        <h5 style="padding: 0.2em;">${_("Linked JupyterHubs")}</h5>
                        <table class="table table-hover table-striped table-sm">
                            <tbody data-bind="foreach: availableServices">
                                <tr>
                                    <td>
                                      <a data-bind="attr: {href: base_url}, text: name" target="_blank"></a>
                                      <a data-bind="attr: {href: import_url}" style="margin-left: 1em;" class="btn btn-default" target="_blank">
                                          <i class="fa fa-external-link"></i> ${_("Launch")}
                                      </a>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <!-- /ko -->
                        <!-- ko if: availableServices().length == 0 -->
                        <div style="margin: 0.5em;">${_("No Linked JupyterHubs")}</div>
                        <!-- /ko -->
                      <!-- /ko -->
                    </div>
                % endif

                % if addon_name == 'iqbrims':
                    <div id="iqbrims-content" class="scripted">
                      <!-- ko if: loading -->
                      <div>${_("Loading")}</div>
                      <!-- /ko -->
                      <!-- ko if: loadFailed -->
                      <div class="text-danger">${_("Error occurred")}</div>
                      <!-- /ko -->
                      <!-- ko if: loadCompleted -->
                        <!-- ko if: modeAdmin -->
                          <i>${_("Management Project")}</i>
                          <div>
                            <a data-bind="attr: {href: flowableTaskUrl}" target="_blank">${_("Flowable Task Service")}</a>
                          </div>
                        <!-- /ko -->
                        <!-- ko ifnot: modeAdmin -->
                          <!-- ko if: isModeSelected -->
                            <!-- ko if: (!isSubmitted() && modeDeposit()) -->
                              <div class="form-group">
                                <button type="button" class="btn btn-primary"
                                        data-bind="click: gotoDepositForm">${_("Deposit Manuscript & Data")}</button>
                                <small class="form-text text-muted" data-bind="text: depositHelp">
                                </small>
                              </div>
                            <!-- /ko -->
                            <!-- ko if: (!isSubmitted() && modeCheck()) -->
                              <div class="form-group">
                                <button type="button" class="btn btn-primary"
                                        data-bind="click: gotoCheckForm">${_("Image Scan only")}</button>
                                <small class="form-text text-muted" data-bind="text: checkHelp">
                                </small>
                              </div>
                            <!-- /ko -->
                            <!-- ko if: isSubmitted -->
                              <div style="margin: 0.5em;">
                                <div data-bind="foreach: formEntries">
                                    <div class="col-sm-4 col-md-4" style="font-weight: bold;" data-bind="text: title">
                                    </div>
                                    <div class="col-sm-8 col-md-8" data-bind="text: value">
                                    </div>
                                </div>
                              </div>
                            <!-- /ko -->
                          <!-- /ko -->
                          <!-- ko ifnot: isModeSelected -->
                          <div class="form-group">
                            <button type="button" class="btn btn-primary"
                                    data-bind="click: gotoDepositForm">${_("Deposit Manuscript & Data")}</button>
                            <small class="form-text text-muted" data-bind="text: depositHelp">
                            </small>
                          </div>
                          <div class="form-group">
                            <button type="button" class="btn btn-primary"
                                    data-bind="click: gotoCheckForm">${_("Image Scan only")}</button>
                            <small class="form-text text-muted" data-bind="text: checkHelp">
                            </small>
                          </div>
                          <!-- /ko -->
                        <!-- /ko -->
                      <!-- /ko -->
                    </div>
                % endif

                </div>
            % else:
                <div class='addon-config-error p-sm'>
                    ${addon_data['full_name']} add-on is not configured properly.
                    % if user['is_contributor_or_group_member']:
                        ${_('Configure this add-on on the <a href=%(nodeUrl)s>add-ons</a> page.') % dict(nodeUrl='"' + h(node['url']) + 'addons/"') | n}
                    % endif
                </div>

            % endif
        </div>
    % endif

</%def>
<%inherit file="../project/addon/widget.mako"/>
