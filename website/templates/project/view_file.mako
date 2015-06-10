<%inherit file="project/project_base.mako"/>

## Use full page width
<%def name="container_class()">container-xxl</%def>

<%def name="title()">${file_name | h}</%def>
<div class="row">
  <div class="col-sm-5">
    <h2 class="break-word">
      ${file_name | h}
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
<div class="row">

  <div id="file-navigation" class="panel-toggle col-sm-3 file-tree">
    <div class="osf-panel osf-panel-hide osf-panel-flex reset-height">
      <div class="osf-panel-header osf-panel-header-flex" style="display:none">
        <div id="filesSearch"></div>
        <div id="toggleIcon" class="pull-right">
          <div class="panel-collapse"><i class="fa fa-angle-left"></i></div>
        </div>
      </div>

      <div class="osf-panel-body osf-panel-body-flex file-page reset-height">
        <div id="grid">
          <div class="fangorn-loading">
            <div class="logo-spin text-center"><img src="/static/img/logo_spin.png" alt="loader"> </div>
            <p class="m-t-sm fg-load-message"> Loading files...  </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Menu toggle closed -->
    <div class="osf-panel osf-panel-show text-center reset-height"  style="display: none">
      <div class="osf-panel-header">
        <i class="fa fa-file"></i>
        <i class="fa fa-angle-right"></i>
      </div>
    </div>
  </div>

  <div id="fileViewPanelLeft" class="col-sm-9 panel-expand">
    <div class="row">
      <div id="mfrIframeParent" class="col-sm-9">
        <div id="mfrIframe" class="mfr mfr-file"></div>
      </div>

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
            size: ${size},
            extra: ${extra},
            error: '${error | js_str}',
            name: '${file_name | js_str}',
            path: '${file_path | js_str}',
            provider: '${provider | js_str}',
            safeName: '${file_name | h,js_str}',
            materializedPath: '${materialized_path | js_str}',
          urls: {
        %if error is None:
              render: '${urls['render']}',
        %endif
              sharejs: '${urls['sharejs'] | js_str}',
            }
        },
        editor: {
            registration: true,
            docId: '${sharejs_uuid}',
            userId: '${user['id']}',
            userName: '${user['fullname'] | js_str}',
            userUrl: '/${user['id']}/',
            userGravatar: '${urls['gravatar']}'.replace('&amp;', '&')
        },
        node: {
          urls: {
            files: '${urls['files'] | js_str}'
          }
        },
        panelsUsed: ['edit', 'view'],
        currentUser: {
          canEdit: ${int(user['can_edit'])}
        }
      });
    </script>

    <link href="${urls['mfr']}/static/css/mfr.css" media="all" rel="stylesheet" />
    <script src="${urls['mfr']}/static/js/mfr.js"></script>

    <script src="//${urls['sharejs']}/text.js"></script>
    <script src="//${urls['sharejs']}/share.js"></script>

    <script src=${"/static/public/js/file-page.js" | webpack_asset}></script>
    <script src=${"/static/public/js/view-file-tree-page.js" | webpack_asset}></script>
</%def>
