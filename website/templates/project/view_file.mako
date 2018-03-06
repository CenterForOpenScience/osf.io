<%inherit file="project/project_base.mako"/>

<div id="alertBar"></div>

## Use full page width
<%def name="container_class()">container-xxl</%def>

<%def name="title()">${file_name | h}</%def>

% if (user['can_comment'] or node['has_comments']) and allow_comments and not node['anonymous']:
    <%include file="include/comment_pane_template.mako"/>
% endif

<div class="row">
  <div class="col-sm-5">
    <h2 class="break-word">
      ## Split file name into two parts: with and without extension
      <span id="fileTitleEditable">${file_name | h}</span>
      <a id='versionLink' class='scripted'>(Version: ${ version_id | h})</a>
      % if file_revision:
        <small>&nbsp;${file_revision | h}</small>
      % endif
    </h2>
  </div>
  <div class="col-sm-7">
    <div id="toggleBar" class="pull-right"></div>
  </div>
</div>
<hr>

%if file_id == node['preprint_file_id'] and node['is_preprint']:
<div class="row">
    <div class="col-xs-12">
        <div class="preprint-notice m-b-md p-md clearfix">
            This is the primary file for a preprint. <a href="http://help.osf.io/m/preprints">Learn more</a> about how to work with preprint files.
            <a href="${node['preprint_url']}" class="btn btn-default btn-sm m-r-xs pull-right">View preprint</a>
            % if user['is_admin']:
                <a href="${node['preprint_url']}edit" class="btn btn-default btn-sm m-r-xs pull-right">Edit preprint</a>
            % endif
        </div>
    </div>
</div>
% endif

<div class="row">

  <div id="file-navigation" class="panel-toggle col-sm-3 file-tree">
    <div class="osf-panel panel panel-default osf-panel-hide osf-panel-flex reset-height">
      <div class="osf-panel-body-flex file-page reset-height">
        <div id="grid">
          <div class="spinner-loading-wrapper">
            <div class="ball-scale ball-scale-blue">
                <div></div>
            </div>
            <p class="m-t-sm fg-load-message"> Loading files...  </p>
          </div>
        </div>
      </div>
    </div>

      <!-- Menu toggle closed -->
      <div class="panel panel-default osf-panel-show text-center reset-height pointer"  style="display: none">
          <div class="row tb-header-row">
              <i class="fa fa-file p-l-xs p-r-xs"></i>
              <div class="fangorn-toolbar-icon">
                  <i class="fa fa-angle-down"></i>
              </div>
          </div>
      </div>
      %if (file_tags or 'write' in user['permissions']) and provider == 'osfstorage' and not error:
       <div class="panel panel-default">
        <div class="panel-heading clearfix">
            <h3 class="panel-title">Tags</h3>
            <div class="pull-right">
            </div>
        </div>
        <div class="panel-body">
            <input id="fileTags" value="${','.join(file_tags) if file_tags else ''}" />
        </div>
        </div>
       %endif
  </div>

<!-- The osf-logo spinner here is from mfr code base -->
  <div id="fileViewPanelLeft" class="col-sm-9 panel-expand">
    <div class="row">
        <div id="externalView" class="col-sm-9"></div>
        <div id="mfrIframeParent" class="col-sm-9">
            <div id="mfrIframe" class="mfr mfr-file"></div>
        </div>

    <!-- This section is built by mithril in revisions.js -->
      <div class="file-view-panels col-sm-3"></div>
    </div>
  </div>
</div>

## Begin Modals
<div class="modal fade" id="connectedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Connected to collaborative file editing</h3>
      </div>
      <div class="modal-body">
        <p>
          This page is currently connected to collaborative file editing. All edits made will be visible to
          contributors with write permission in real time. Changes will be stored
          but not published until you click the "Save" button.
        </p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="connectingModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Connecting to collaborative file editing</h3>
      </div>
      <div class="modal-body">
        <p>
          This page is currently attempting to connect to collaborative file editing. You may continue to make edits.
          <strong>Changes will not be saved until you press the "Save" button.</strong>
        </p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="disconnectedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Collaborative file editing is unavailable</h3>
      </div>
      <div class="modal-body">
        <p>
          Collaborative file editing is currently unavailable. You may continue to make edits.
          <strong>Changes will not be saved until you press the "Save" button.</strong>
        </p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="unsupportedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Browser unsupported</h3>
      </div>
      <div class="modal-body">
        <p>
          Your browser does not support collaborative editing. You may continue to make edits.
          <strong>Changes will not be saved until you press the "Save" button.</strong>
        </p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>
## End Modals block

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    % for script in tree_js:
        <script type="text/javascript" src="${script | webpack_asset}"></script>
    % endfor

    % if 'osf.io' in domain:
    <script>
        // IE10 Same Origin (CORS) fix
        document.domain = 'osf.io';
    </script>
    %endif
    <script type="text/javascript">
      window.contextVars = $.extend(true, {}, window.contextVars, {
        file: {
            size: ${size | sjson, n },
            extra: ${extra | sjson, n },
            error: ${ error | sjson, n },
            privateRepo: ${ private | sjson, n },
            name: ${ file_name | sjson, n },
            path: ${ file_path | sjson, n },
            provider: ${ provider | sjson, n },
            safeName: ${ file_name | h, sjson},
            materializedPath: ${ materialized_path | sjson, n },
            file_tags: ${file_tags if file_tags else False| sjson, n},
            guid: ${file_guid | sjson, n},
            id: ${file_id | sjson, n},
            checkoutUser: ${checkout_user if checkout_user else None | sjson, n},
            isPreregCheckout: ${pre_reg_checkout if pre_reg_checkout else False | sjson, n},
          urls: {
        %if error is None:
              render: ${ urls['render'] | sjson, n },
        %endif
              sharejs: ${ urls['sharejs'] | sjson, n },
            }
        },
        editor: {
            registration: true,
            docId: ${ sharejs_uuid | sjson, n },
            userId: ${ user['id'] | sjson, n },
            userName: ${ user['fullname'] | sjson, n },
            userUrl: ${ ('/' + user['id'] + '/') if user['id'] else None | sjson, n },
            userProfileImage: ${ urls['profile_image'].replace('&amp;', '&') | sjson, n }
        },
        node: {
          urls: {
            files: ${ urls['files'] | sjson, n }
          }
        },
        panelsUsed: ['edit', 'view'],
        currentUser: {
          canEdit: ${ int(user['can_edit']) | sjson, n }
        },
        analyticsMeta: {
            pageMeta: {
                title: 'File: ' + ${file_name | sjson, n},
                public: true,
            },
        },
      });
      window.contextVars.file.urls.external = window.contextVars.file.extra.webView;
    </script>

    <link href="/static/css/pages/file-view-page.css" rel="stylesheet" />
    <link href="${urls['mfr']}/static/css/mfr.css" media="all" rel="stylesheet" />
    <script src="${urls['mfr']}/static/js/mfr.js"></script>

    <script src="//${urls['sharejs']}/text.js"></script>
    <script src="//${urls['sharejs']}/share.js"></script>

    <script src=${"/static/public/js/file-page.js" | webpack_asset}></script>
    <script src=${"/static/public/js/view-file-tree-page.js" | webpack_asset}></script>
</%def>
