<%inherit file="project/project_base.mako"/>
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

      <div class="col-md-8">
        <div id="fileRendered" class="mfr mfr-file">
          % if rendered is not None:
            ${rendered}
          % else:
            <img src="/static/img/loading.gif">
          % endif
        </div>
      </div>

      <div class="col-md-4">
        <div id="fileRevisions" class="scripted">
          <ol class="breadcrumb">
            <li><a href="{{ node.urls.files }}" data-bind="text: node.title"></a></li>
            <li class="active overflow" data-bind="text: file.provider"></li>
            <li class="active overflow" data-bind="text: file.name"></li>
          </ol>

          <a class="btn btn-success btn-md" href="{{ currentVersion().osfDownloadUrl }}" data-bind="click: currentVersion().download">
            Download <i class="icon-download-alt"></i>
          </a>
          <button class="btn btn-danger btn-md" data-bind="click: askDelete, if: editable">
            Delete <i class="icon-trash"></i>
          </button>


          <table class="table" data-bind="if: versioningSupported">
            <thead>
              <tr>
                <th>Version</th>
                <th>Date</th>
                <th data-bind="if: userColumn">User</th>
                <th>Download</th>
              </tr>
            </thead>

            <tbody data-bind="foreach: {data: revisions, as: 'revision'}">
              <tr data-bind="css: $parent.isActive(revision)">
                <td>
                  <a href="{{ revision.osfViewUrl }}" data-bind="if: revision !== $parent.currentVersion()">
                    {{ revision.version.substring(0, 8) }}
                  </a>
                  <span data-bind="if: revision === $parent.currentVersion()">
                    {{ revision.version.substring(0, 8) }}
                  </span>
                </td>
                <td>{{ revision.displayDate }}</td>
                <td data-bind="if: $parent.userColumn">
                  <a data-bind="if: revision.extra.user.url"
                    href="{{ revision.extra.user.url }}">
                    {{ revision.extra.user.name }}
                  </a>
                  <span data-bind="ifnot: revision.extra.user.url">
                    {{ revision.extra.user.name }}
                  </span>
                </td>
                <td>
                  <span class="badge" data-bind="if: revision.extra.downloads">
                    {{ revision.extra.downloads }}
                  </span>
                  <a class="btn btn-primary btn-sm" href="{{ revision.osfDownloadUrl }}"
                    data-bind="click: revision.download">
                    <i class="icon-download-alt"></i>
                  </a>
                </td>
              </tr>
            </tbody>
          </table>

          <div data-bind="ifnot: versioningSupported">
            <hr>
            <div class="alert alert-warning" role="alert">
              {{ errorMessage }}
            </div>
          </div>

        </div>
      </div>
    </div>

  </div>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
        <script type="text/javascript">
          window.contextVars = $.extend(true, {}, window.contextVars, {
            renderURL: ${"'{}'".format(render_url) if rendered is None else 'undefined'},
            file: {
                name: '${file_name | js_str}',
                path: '${file_path | js_str}',
                provider: '${provider | js_str}'
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
