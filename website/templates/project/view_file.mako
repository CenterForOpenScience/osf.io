<%inherit file="project/project_base.mako"/>
<%def name="title()">Loading...</%def>

<div id="fileViewPage"></div>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
        <script type="text/javascript">
          window.contextVars = $.extend(true, {}, window.contextVars, {
            renderUrl: '${render_url | js_str}',
            file: {
                path: '${file_path | js_str}',
                provider: '${provider | js_str}',
            },
            node: {
              urls: {
                files: '${files_url | js_str}'
              }
            },
            currentUser: {
              canEdit: ${int(user['can_edit'])}
            }
          });
        </script>
        <script src=${"/static/public/js/view-file-page.js" | webpack_asset}></script>
</%def>
