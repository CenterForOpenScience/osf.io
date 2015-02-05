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

        <a class="btn btn-success btn-md" href="{{ urls.download }}">
          Download <i class="icon-download-alt"></i>
        </a>
        <!-- ko if: editable -->
        <button class="btn btn-danger btn-md" data-bind="click: askDelete">
          Delete <i class="icon-trash"></i>
        </button>
        <!-- /ko -->


        <!-- ko if: versioningSupported -->
        <table class="table osfstorage-revision-table ">

            <thead>
                <tr>
                    <th>Version</th>
                    <th>Date</th>
                    <!-- ko if: revisions()[0] && revisions()[0].extra && revisions()[0].extra.user -->
                    <th>User</th>
                    <!-- /ko -->
                    <th>Download</th>
                </tr>
            </thead>

            <tbody data-bind="foreach: {data: revisions, as: 'revision'}">
                <tr>
                    <td>
                      <a href="{{ '?' + revision.versionIdentifier + '=' + revision.version }}">
                        {{ revision.version.substring(0, 8) }}
                      </a>
                    </td>
                    <td>{{ revision.displayDate }}</td>
                    <!-- ko if: revision.extra && revision.extra.user -->
                    <td>
                      <!-- ko if: revision.extra.user.url -->
                      <a href="{{ revision.extra.user.url }}">
                        {{ revision.extra.user.name }}
                      </a>
                    <!-- /ko -->
                    <!-- ko ifnot: revision.extra.user.url -->
                        {{ revision.extra.user.name }}
                    <!-- /ko -->
                    </td>
                    <!-- /ko -->
                    <td>
                      <!-- ko if: revision.extra && revision.extra.downloads -->
                      <span class="badge">{{ revision.extra.downloads }}</span>
                      <!-- /ko -->
                      <a class="btn btn-primary btn-sm" href="{{ revision.downloadUrl }}">
                        <i class="icon-download-alt"></i>
                      </a>
                    </td>
                </tr>
            </tbody>

        </table>

        <p data-bind="if: more">
            <a data-bind="click: fetch">More versions...</a>
        </p>
        <!-- /ko -->

        <!-- ko ifnot: versioningSupported -->
          <hr>

          <div class="alert alert-warning" role="alert">
            {{ errorMessage }}
          </div>
        <!-- /ko -->

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
