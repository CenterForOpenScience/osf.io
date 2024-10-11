<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} ${_("Wiki")}</%def>
<head>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
</head>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/wiki-page.css">
</%def>
## Use full page width
<%def name="container_class()">container-xxl</%def>

% if (user['can_comment'] or node['has_comments']) and not node['anonymous']:
    <%include file="include/comment_pane_template.mako"/>
% endif
<style >

.ProseMirror:focus {
    outline: none;
  }

</style>

<div class="row" style="margin-bottom: 5px;">
    <div class="col-sm-6">
        <%include file="wiki/templates/status.mako"/>
    </div>
    <div class="col-sm-6">
        <div class="pull-right m-t-md">
          <div class="switch"></div>
          </div>
    </div>
</div>

    <div class="row wiki-wrapper">
        <div class="panel-toggle col-sm-${'4' if 'menu' in panels_used else '1'}">

            <!-- Menu with toggle normal -->
            <div class="osf-panel panel panel-default reset-height ${'' if 'menu' in panels_used else 'hidden visible-xs'}" data-bind="css: {  'osf-panel-flex': !$root.singleVis() }">
                <div class="panel-heading wiki-panel-header clearfix" data-bind="css: {  'osf-panel-heading-flex': !$root.singleVis()}" style="padding-left: 5px; padding-right: 10px;">
                    % if user['can_edit']:
                        <div class="wiki-toolbar-icon text-success" data-toggle="modal" data-target="#newWiki">
                            <i class="fa fa-plus text-success"></i><span>${_("New")}</span>
                        </div>
                        % if sortable_pages_ctn > 1:
                            <div class="wiki-toolbar-icon text-success" data-toggle="modal" data-target="#sortWiki">
                                <i class="fa fa-sort text-info"></i><span>${_("Reorder")}</span>
                            </div>
                        % endif
                        % if user['can_wiki_import']:
                            % if len(import_dirs) > 0:
                                % if alive_task_id:
                                    <div class="wiki-toolbar-icon text-success" style="pointer-events:none; opacity: 0.4;">
                                      <i class="fa fa-upload text-success"></i><span>${_("Importing")}</span>
                                    </div>
                                    <div class="wiki-toolbar-icon text-danger" data-toggle="modal" data-target="#abortWikiImport">
                                      <i class="fa fa-trash-o text-danger"></i><span>${_("Abort")}</span>
                                    </div>
                                % else:
                                    <div class="wiki-toolbar-icon text-success" data-toggle="modal" data-target="#wikiImport">
                                      <i class="fa fa-upload text-success"></i><span>${_("Import")}</span>
                                    </div>
                                % endif
                            % endif
                        % endif
                        % if wiki_id and wiki_name != 'home':
                            <div class="wiki-toolbar-icon text-danger" data-toggle="modal" data-target="#deleteWiki">
                                <i class="fa fa-trash-o text-danger"></i><span>${_("Delete")}</span>
                            </div>
                        % endif
                    % else:
                        <h3 class="panel-title"> <i class="fa fa-list"></i>  ${_("Menu")} </h3>
                    % endif
                    <div id="toggleIcon" class="pull-right hidden-xs">
                        <div class="panel-collapse pointer"><i class="fa fa-angle-left"></i></div>
                    </div>
                </div>
                <div id="grid">
                    <div class="spinner-loading-wrapper">
                        <div class="ball-scale ball-scale-blue">
                            <div></div>
                        </div>
                        <p class="m-t-sm fg-load-message"> ${_("Loading wiki pages...")}  </p>
                    </div>
                </div>
                <div class="hidden text-danger p-md" id="wikiErrorMessage"></div>
            </div>

            <!-- Menu with toggle collapsed -->
            <div class="osf-panel panel panel-default panel-collapsed hidden-xs text-center ${'hidden' if 'menu' in panels_used else ''}" >
                <div class="panel-heading pointer">
                    <i class="fa fa-list"> </i>
                    <i class="fa fa-angle-right"> </i>
                </div>
                <div>
                    <%include file="wiki/templates/nav.mako"/>
                </div>
            </div>
        </div>

    <div class="wiki" id="wikiPageContext">
    <div class="panel-expand col-sm-${'8' if 'menu' in panels_used else '11'}">
      <div class="row">

          <div data-osf-panel="${_('View')}"
               class="${'col-sm-{0}'.format(12 / num_columns)}"
               style="${'' if 'view' in panels_used else 'display: none'}">
              <div class="osf-panel panel panel-default no-border" data-bind="css: { 'no-border reset-height': $root.singleVis() === 'view', 'osf-panel-flex': $root.singleVis() !== 'view' }">
                <div class="panel-heading wiki-panel-header wiki-single-heading" data-bind="css: { 'osf-panel-heading-flex': $root.singleVis() !== 'view', 'wiki-single-heading': $root.singleVis() === 'view' }">
                    <div class="row wiki-view-icon-container">
                        <div class="col-sm-12">
                          % if user['can_edit_wiki_body']:
                            <div id="editWysiwyg" class="wiki-toolbar-icon text-info" data-bind="click: editMode">
                                <i class="fa fa-edit text-info"></i><span>${_("Edit")}</span>
                            </div>
                            <div id="collaborativeStatus" class="pull-right m-l-md" style="display: none">
                              <div class="progress no-margin pointer" data-toggle="modal" data-bind="attr: {'data-target': modalTarget}" >
                                <div role="progressbar" data-bind="attr: progressBar">
                                  <span class="progress-bar-content p-h-sm">
                                    <span data-bind="text: statusDisplay"></span>
                                    <span class="sharejs-info-btn">
                                      <i class="fa fa-question-circle fa-large"></i>
                                    </span>
                                 </span>
                                </div>
                              </div>
                            </div>
                          % endif
                            <div class="pull-right">
                              <!-- Version Picker -->
                              <span>${_("Wiki Version:")}</span>
                              <div style="display: inline-block">
                                <select class="form-control" data-bind="value:viewVersion" id="viewVersionSelect">
                                  % if user['can_edit_wiki_body']:
                                      <option value="preview" ${'selected' if version_settings['view'] == 'preview' else ''}>${_("Preview")}</option>
                                  % endif
                                  % if len(versions) > 0:
                                      <option value="current" ${'selected' if version_settings['view'] == 'current' else ''}>${_("(Current)")} ${versions[0]['user_fullname']}: ${versions[0]['date']}</option>
                                  % else:
                                      <option value="current" ${'selected' if version_settings['view'] == 'current' else ''}>${_("Current")}</option>
                                  % endif
                                  % if len(versions) > 1:
                                      % for version in versions[1:]:
                                          <option value="${version['version']}" ${'selected' if version_settings['view'] == version['version'] else ''}>(${version['version']}) ${version['user_fullname']}: ${version['date']}</option>
                                      % endfor
                                  % endif
                                </select>
                              </div>
                            </div>

                        </div>
                    </div>
                </div>

                <div id="wikiViewPanel"  class="panel-body" data-bind="css: { 'osf-panel-body-flex': $root.singleVis() !== 'view' }">
                  <div id="mMenuBar" style="display: none; border-bottom: 1px solid; border-bottom-color: #d1d5db">
                    <button id="undoWiki" class="menuItem" data-bind="click: undoWiki" disabled><span id="msoUndo" class="material-symbols-outlined" style="opacity: 0.3">undo</span></button>
                    <button id="redoWiki" class="menuItem" data-bind="click: redoWiki" disabled><span id="msoRedo" class="material-symbols-outlined" style="opacity: 0.3">redo</span></button>
                    <button id="strongWiki" class="menuItem" data-bind="click: strong"><span class="material-symbols-outlined" >format_bold</span></button>
                    <button id="italicWiki" class="menuItem" data-bind="click: italic"><span class="material-symbols-outlined">format_italic</span></button>
                    <button class="menuItem" data-bind="click: strikethrough"><span class="material-symbols-outlined">format_strikethrough</span></button>
                    <button class="menuItem" data-bind="click: underline"><span class="material-symbols-outlined">format_underlined</span></button>
                    <button class="menuItem" style="position: relative; display:inline-block"><span class="material-symbols-outlined">format_color_text</span><input type="color" data-bind="value: color, event: { change: colortext }" style="position: absolute; top:0; left:0; width: 100%; height: 100%; opacity: 0; cursor: pointer"></button>
                    <button class="menuItem" data-bind="click: mokujimacro"><span class="material-symbols-outlined">sort</span></button>
                    <button class="menuItem" data-bind="click: getLinkInfo" data-toggle="modal" data-target="#toggleLink"><span class="material-symbols-outlined" >link</span></button>
                    <button class="menuItem" data-bind="click: quote"><span class="material-symbols-outlined">format_quote</span></button>
                    <button class="menuItem" data-bind="click: code"><span class="material-symbols-outlined">code</span></button>
                    <button class="menuItem"  data-bind="click: getImageInfo" data-toggle="modal" data-target="#toggleImage"><span class="material-symbols-outlined">image</span></button>
                    <button class="menuItem" data-bind="click: listNumbered"><span class="material-symbols-outlined">format_list_numbered</span></button>
                    <button class="menuItem" data-bind="click: listBulleted"><span class="material-symbols-outlined">format_list_bulleted</span></button>
                    <button class="menuItem" data-bind="click: head"><span class="material-symbols-outlined">view_headline</span></button>
                    <button class="menuItem" data-bind="click: horizontal"><span class="material-symbols-outlined">horizontal_rule</span></button>
                    <div style="display: inline-block; position:absolute">
                    <button id="tableBtn" class="menuItem" data-bind="click: table"><span class="material-symbols-outlined">table</span><span id="arrowDropDown" class="material-symbols-outlined" style="margin-left: -7px; display: none;">arrow_drop_down</span></button>
                      <div id="tableMenu" class="table-dropdown-menu" style="display: none; border: 1px solid #aaa; padding: 2px; font-size: 90%; background: white; z-index: 15; white-space: nowrap; position: absolute">
                        <div class="table-dropdown-item" data-bind="click: addColumnBef"><div>${_("Insert column before")}</div></div>
                        <div class="table-dropdown-item" data-bind="click: addColumnAft"><div>${_("Insert column after")}</div></div>
                        <div class="table-dropdown-item" data-bind="click: addRowBef"><div>${_("Insert row before")}</div></div>
                        <div class="table-dropdown-item" data-bind="click: addRowAft"><div>${_("Insert row after")}</div></div>
                        <div class="table-dropdown-item" data-bind="click: deleteSelectedCell"><div>${_("delete cell")}</div></div>
                        <div class="table-dropdown-item" data-bind="click: deleteTable"><div>${_("delete table")}</div></div>
                      </div>
                    </div>
                    <button class="menuItem" style="margin-left: 40px;" data-toggle="modal" data-target="#wiki-help-modal"><span class="material-symbols-outlined">help</span></button>
                  </div>
                  <div id="mEditor" class="mFrame" style="${'' if version_settings['view'] == 'preview' else 'display: none'}"></div>

                  <div id="wikiViewRender">
                      % if wiki_markdown:
                          <div id="mView" class="mFrame"></div>
                      % else:
                          <p class="text-muted"><em>${_("Add important information, links, or images here to describe your project.")}</em></p>
                      % endif
                  </div>
                </div>
                  <div id="mEditorFooter" class="panel-footer" style="display: none">
                      <div class="row">
                        <div class="col-xs-12">
                          <div class="pull-right">
                              <button id="revert-button"
                                      class="btn"
                                      data-bind="click: editModeOff"
                                      >${_("Close")}</button>
                              <input type="submit"
                                    class="btn btn-success"
                                    value="${_('Save')}"
                                    data-bind="click: submitMText">
                          </div>
                        </div>
                      </div>

                  </div>
              </div>
          </div>


          <div id="compareWidget" data-osf-panel="${_('Compare')}"
               class="${'col-sm-{0}'.format(12 / num_columns)}"
               style="${'' if 'compare' in panels_used else 'display: none'}">
            <div class="osf-panel panel panel-default osf-panel-flex" data-bind="css: { 'no-border reset-height': $root.singleVis() === 'compare', 'osf-panel-flex': $root.singleVis() !== 'compare' }">
              <div class="panel-heading osf-panel-heading-flex" data-bind="css: {  'osf-panel-heading-flex': $root.singleVis() !== 'compare', 'wiki-single-heading': $root.singleVis() === 'compare'}">
                  <div class="row">
                      <div class="col-xs-12">
                          <span class="panel-title m-r-xs"> <i class="fa fa-exchange"> </i>   ${_("Compare")} </span>
                          <div class="inline" data-bind="css: { 'pull-right' :  $root.singleVis() === 'compare' }">
                            <!-- Version Picker -->
                            <span class="compare-version-text"><i> <span data-bind="text: viewVersionDisplay"></span></i>${_(" to")}
                              <select class="form-control" data-bind="value: compareVersion" id="compareVersionSelect">
                                  % if len(versions) > 0:
                                      <option value="current" ${'selected' if version_settings['compare'] == 'current' else ''}>${_("(Current)")} ${versions[0]['user_fullname']}: ${versions[0]['date']}</option>
                                  % else:
                                      <option value="current" ${'selected' if version_settings['view'] == 'current' else ''}>${_("Current")}</option>
                                  % endif
                                  % if len(versions) > 1:
                                      % for version in versions[1:]:
                                          <option value="${version['version']}" ${'selected' if version_settings['compare'] == version['version'] else ''}>(${version['version']}) ${version['user_fullname']}: ${version['date']}</option>
                                      % endfor
                                  % endif

                              </select></span>

                          </div>

                      </div>
                  </div>
              </div>
              <div data-bind="html: renderedCompare, css: { 'osf-panel-body-flex': $root.singleVis() !== 'compare' }" class="panel-body wiki-compare-view">
              </div>
            </div>
          </div>
      </div><!-- end row -->
    </div>

  </div>
</div><!-- end wiki -->

<!-- Wiki modals should also be placed here! -->
  <%include file="wiki/templates/add_wiki_page.mako"/>
  <%include file="wiki/templates/import_wiki_page.mako"/>
  <%include file="wiki/templates/sort_wiki_page.mako"/>
  <%include file="wiki/templates/abort_wiki_import.mako"/>
  <%include file="wiki/templates/wiki-bar-modal-help.mako"/>
% if wiki_id and wiki_name != 'home':
  <%include file="wiki/templates/delete_wiki_page.mako"/>
% endif


<div class="modal fade" id="permissionsModal">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">${_("Page permissions have changed")}</h3>
      </div>
      <div class="modal-body">
        <p>${_("Your browser should refresh shortly")}&hellip;</p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="renameModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="spinner-loading-wrapper">
                <div class="ball-scale ball-scale-blue">
                    <div></div>
                </div>
                 <p class="m-t-sm fg-load-message"> ${_("Renaming wiki...")}  </p>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="deleteModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">${_("Wiki page deleted")}</h3>
      </div>
      <div class="modal-body">
        <p>${_("Press Confirm to return to the project wiki home page.")}</p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-success" data-dismiss="modal">${_("Confirm")}</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="connectedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">${_("Connected to the collaborative wiki")}</h3>
      </div>
      <div class="modal-body">
        <p>
            ${_('This page is currently connected to the collaborative wiki. All edits made will be visible to\
            contributors with write permission in real time. Changes will be stored\
            but not published until you click the "Save" button.')}
        </p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-default" data-dismiss="modal">${_("Close")}</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="connectingModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">${_("Connecting to the collaborative wiki")}</h3>
      </div>
      <div class="modal-body">
        <p>
            ${_("This page is currently attempting to connect to the collaborative wiki. You may continue to make edits.")}
            <strong> ${_('Changes will not be saved until you press the "Save" button.')}</strong>
        </p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="disconnectedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">${_("Collaborative wiki is unavailable")}</h3>
      </div>
      <div class="modal-body">
        <p>
            ${_("The collaborative wiki is currently unavailable. You may continue to make edits.")}
            <strong>${_('Changes will not be saved until you press the "Save" button.')}</strong>
        </p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="unsupportedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">${_("Browser unsupported")}</h3>
      </div>
      <div class="modal-body">
        <p>
            ${_("Your browser does not support collaborative editing. You may continue to make edits.")}
            <strong>${_('Changes will not be saved until you press the "Save" button.')}</strong>
        </p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="toggleLink" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h4 class="modal-title">${_("Add Hyperlink")}</h4>
      </div>
      <div class="modal-body">
        <div class="m-b-sm">
          <p class="wikiEditorModalLabel">${_("Link URL:")}</p>
          <input id="linkSrc" class="form-control wikiEditorModalInput" type="text" placeholder="${_('Enter link URL')}">
        </div>
        <div class="m-b-sm">
          <p class="wikiEditorModalLabel">${_("Link Tooltip:")}</p>
          <input id="linkTitle" class="form-control wikiEditorModalInput" type="text" placeholder="${_('Enter link Tooltip')}">
        </div>
      </div>
      <div class="modal-footer">
        <div class="pull-right">
          <button
            class="btn"
            data-dismiss="modal"
          >${_("Cancel")}</button>
          <button
            id="addLink"
            class="btn btn-success"
          >${_("Add")}</button>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="toggleImage" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h4 class="modal-title">${_("Add Image")}</h4>
      </div>
      <div class="modal-body">
        <div class="m-b-sm">
          <p class="wikiEditorModalLabel">${_("Image URL:")}</p>
          <input id="imageSrc" data-bind="textInput: imageSrcInput" class="form-control wikiEditorModalInput" type="text" placeholder="${_('Enter image URL')}">
        </div>
        <div class="m-b-sm">
          <p class="wikiEditorModalLabel">${_("Image ToolTip:")}</p>
          <input id="imageTitle" class="form-control wikiEditorModalInput" type="text" placeholder="${_('Enter image tooltip')}">
        </div>
        <div class="m-b-sm">
          <p class="wikiEditorModalLabel">${_("Alternative Text:")}</p>
          <input id="imageAlt" class="form-control wikiEditorModalInput" type="text" placeholder="${_('Enter Alternative Text')}">
        </div>
        <div class="m-b-sm">
          <p class="wikiEditorModalLabel">${_("Image Size:")}</p>
          <input id="imageWidth"  data-bind="textInput: imageWidthInput" class="form-control wikiEditorModalInput" type="text" placeholder="${_('Enter image size (e.g., 300 for pixels, or 50% for percentage)')}" style="font-size:10px">
          <div id="sizeError" class="text-danger" style="display: none;" data-bind="visible: showSizeError">${_("Invalid size format. Use pixels or percentage.")}</div>
        </div>
      </div>
      <div class="modal-footer">
        <div class="pull-right">
          <button
            class="btn"
            data-dismiss="modal"
          >${_("Cancel")}</button>
          <button
            id="addImage"
            class="btn btn-success"
          >${_("Add")}</button>
        </div>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script>

    var canEditBody = ${user['can_edit_wiki_body'] | sjson, n};
    var isContributor = ${user['can_edit']  | sjson, n};

    var canEditPageName = isContributor && ${(wiki_id and wiki_name != 'home') | sjson, n };

    window.contextVars = window.contextVars || {};
    window.contextVars.wiki = {
        canEdit: canEditBody,
        canEditPageName: canEditPageName,
        renderedBeforeUpdate: ${ rendered_before_update | sjson, n },
        versionSettings: ${ version_settings | sjson, n },
        panelsUsed: ${ panels_used | sjson, n },
        wikiID: ${ wiki_id | sjson, n },
        wikiName: ${wiki_name | sjson, n },
        urls: {
            draft: ${ urls['api']['draft'] | sjson, n },
            content: ${urls['api']['content'] | sjson, n },
            rename: ${urls['api']['rename'] | sjson, n },
            grid: ${urls['api']['grid'] | sjson, n },
            sort: ${urls['api']['sort'] | sjson, n },
            page: ${urls['web']['page'] | sjson, n },
            base: ${urls['web']['base'] | sjson, n },
            y_websocket: ${ y_websocket_url | sjson, n }
        },
        metadata: {
            registration: true,
            docId: ${ sharejs_uuid | sjson, n },
            userId: ${user_id | sjson, n },
            userName: ${ user_full_name | sjson, n },
            userUrl: ${ user_url | sjson, n },
            userProfileImage: ${ urls['profile_image'] | sjson, n }.replace('&amp;', '&')
        }
    };
    window.contextVars.analyticsMeta = $.extend(true, {}, window.contextVars.analyticsMeta, {
        pageMeta: {
            title: 'Wiki: ' + ${wiki_name | sjson, n },
            public: true,
        },
    });

</script>
<link href="${node['mfr_url']}/static/css/mfr.css" media="all" rel="stylesheet" />
<script src="${node['mfr_url']}/static/js/mfr.js"></script>
<script src=${"/static/js/pages/wiki-edit-page.js"}></script>
</%def>
