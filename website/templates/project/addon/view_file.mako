<%inherit file="../project_base.mako"/>

## Use full page width
<%def name="container_class()">container-xxl</%def>

<%def name="title()">${file_name}</%def>

    <div>
        <h2 class="break-word">
            ${file_name | h}
            % if file_revision:
                <small>&nbsp;${file_revision | h}</small>
            % endif
        </h2>
        <hr />
    </div>

<div id="file-container" class="row">
    <div id="file-navigation" class="panel-toggle col-md-3">
        <div class="osf-panel osf-panel-flex hidden-xs">
            <div class="osf-panel-header osf-panel-header-flex" style="display:none">
                <div id="filesSearch"></div>
                <div id="toggleIcon" class="pull-right">
                    <div class="panel-collapse"> <i class="fa fa-angle-left"> </i> </div>
                </div>
            </div>
            <div class="osf-panel-body osf-panel-body-flex file-page">
                <div id="grid">
                    <div class="fangorn-loading"> <i class="fa fa-spinner fangorn-spin"></i> <p class="m-t-sm fg-load-message"> Loading files...  </p> </div>
                </div>
            </div>
        </div>

        <!-- Menu toggle closed -->
        <div class="osf-panel panel-collapsed hidden-xs text-center"  style="display: none">
            <div class="osf-panel-header">
                <i class="fa fa-file"> </i>
                <i class="fa fa-angle-right"> </i>
            </div>
        </div>

    </div>

    <div class="col-md-6">
        ${self.file_contents()}
    </div>

    <div class="col-md-3">
        ${self.file_versions()}
    </div>

</div>


<%def name="file_contents()">


    <div id="fileRendered" class="mfr mfr-file">
        % if rendered is not None:
            ${rendered}
        % else:
            <img src="/static/img/loading.gif">
        % endif
    </div>

</%def>

<%def name="file_versions()"></%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    % for script in tree_js:
        <script type="text/javascript" src="${script | webpack_asset}"></script>
    % endfor
    % if rendered is None:
        <script type="text/javascript">
            window.contextVars = window.contextVars || {};
            window.contextVars.renderURL = '${render_url}';
        </script>
        <script src=${"/static/public/js/view-file-page.js" | webpack_asset}></script>
    % else:
        <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
                file: {
                    name: '${file_name | js_str}',
                    path: '${path | js_str}',
                    provider: 'dataverse'
                },
                node: {
                    urls: {
                        files: '${urls['files'] | js_str}'
                    }
                }
        });
        </script>
        <script src=${"/static/public/js/view-file-tree-page.js" | webpack_asset}></script>
    % endif
</%def>
