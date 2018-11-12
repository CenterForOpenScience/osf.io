<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Timestamp</%def>

<div class="page-header  visible-xs">
  <h2 class="text-300">Timestamp</h2>
</div>

<div class="row">
    <div class="col-sm-5">
        <h2 class="break-word">
            Timestamp Control
        </h2>
    </div>
    <div class="col-sm-7">
        <div id="toggleBar" class="pull-right"></div>
    </div>
</div>
<hr/>
<div class="row project-page">

    <!-- Begin left column -->
    <div class="col-md-3 col-xs-12 affix-parent scrollspy">
        <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="0" data-offset-bottom="263">
            <!-- Begin sidebar -->
            <ul class="nav nav-stacked nav-pills">
                <li class="active"><a href="#">Timestamp Error</a></li>
            </ul>
        </div>
    </div>

    <div class="col-md-9 col-xs-12">
        <form id="timestamp-form" class="form">
            <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
                <span>
                    <button type="button" class="btn btn-success" id="btn-verify">Verify</button>
                    <button type="button" class="btn btn-success" id="btn-addtimestamp">Request Trusted Timestamp</button>
                </span>
            </div>
            <span id="configureNodeAnchor" class="anchor"></span>
            <table class="table table-bordered table-addon-terms">
                <thead class="block-head">
                    <tr>
                        <th width="3%"><input type="checkBox" id="addTimestampAllCheck" style="width: 15px; height: 15px;"/></th>
                        <th width="40%">File Path</th>
                        <th width="15%">Timestamp Update User</th>
                        <th width="22%">Timestamp Update Date</th>
                        <th widht="20%">Timestamp Verification</th>
                    </tr>
                </thead>
                <font color="red">
                    <div id="timestamp_errors_spinner" class="spinner-loading-wrapper">
                        <div class="logo-spin logo-lg"></div>
                        <p class="m-t-sm fg-load-message"> Loading timestamp error list ...  </p>
                    </div>
                </font>
                <tbody id="tree_timestamp_error_data">
                </tbody>
            </table>
        </form>
    </div>
</div>

<style type="text/css">
    .table>thead>tr>th {
        vertical-align: middle;
    }
</style>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    % for script in tree_js:
        <script type="text/javascript" src="${script | webpack_asset}"></script>
    % endfor
    <script>
        window.contextVars.project_file_list = window.contextVars.project_file_list || {};
        window.contextVars.project_file_list = ${provider_list| sjson, n }
    </script>

    <script src=${"/static/public/js/timestamp-page.js" | webpack_asset}></script>
</%def>

<script>
    $(function () {
        var btnVerify_onclick = function (event) {
            if($("#btn-verify").attr("disabled") != undefined || $("#btn-addtimestamp").attr("disabled") != undefined) {
                return false;
            }

            $("#btn-verify").attr("disabled", true);
            $("#btn-addtimestamp").attr("disabled", true);
            $("#timestamp_errors_spinner").text("Storage files list gathering ...");
            var post_data = {}
            var fileCnt = 0;
            $.ajax({
                beforeSend: function () {
                    $("#timestamp_errors_spinner").show();
                },
                url: 'json/',
                data: post_data,
                dataType: 'json'
            }).done(function(project_file_list) {
                project_file_list = project_file_list.provider_list;
                for (var i = 0; i < project_file_list.length; i++) {
                    var file_list = project_file_list[i].provider_file_list;
                    for (var j = 0; j < file_list.length; j++) {
                       fileCnt++;
                    }
                }
                var index = 0;
                var successCnt = 0;
                for (var i = 0; i < project_file_list.length; i++) {
                    var provider_tr = '<tr><td colspan="4">' + project_file_list[i].provider + '</td></tr>';
                    var file_list = project_file_list[i].provider_file_list;
                    var provider_output_flg = false;
                    for (var j = 0; j < file_list.length; j++) {
                        var post_data = {'provider': project_file_list[i].provider,
                                         'file_id': file_list[j].file_id,
                                         'file_path': file_list[j].file_path,
                                         'file_name': file_list[j].file_name,
                                         'version': file_list[j].version};
                        $.ajax({
                             url:  nodeApiUrl + 'timestamp/timestamp_error_data/',
                             data: post_data,
                             dataType: 'json'
                          }).done(function(data) {
                                  successCnt++;
                                  $("#timestamp_errors_spinner").text("Verification files : " + successCnt + " / " + fileCnt + " ...");
                                  if (successCnt == fileCnt) {
                                     $("#timestamp_errors_spinner").text("Verification (100%) and Refreshing...");
                                     window.location.reload();
                                  }
                          }).fail(function(xhr, status, error) {
                                  $("#btn-verify").removeAttr("disabled");
                                  $("#btn-addtimestamp").removeAttr("disabled");
                                  $("#timestamp_errors_spinner").text("Error : " + file_list[j].file_path);
                                  Raven.captureMessage('Timestamp Add Error: ' + filePathList[index], {
                                       extra: {
                                           url: url,
                                           status: status,
                                           error: error
                                       }
                                  });
                          });
                    }
                }
            }).fail(function(xhr, textStatus, error) {
               $("#btn-verify").removeAttr("disabled");
               $("#btn-addtimestamp").removeAttr("disabled");
               $("#timestamp_errors_spinner").text("Error : Storage files list gathering Failed");
               Raven.captureMessage('Timestamp Add Error', {
                   extra: {
                      url: url,
                      textStatus: textStatus,
                      error: error
                   }
               });
            });
        };

        var btnAddtimestamp_onclick = function(event) {
            if($("#btn-verify").attr("disabled") != undefined || $("#btn-addtimestamp").attr("disabled") != undefined) {
                return false;
            }

            inputCheckBoxs = $('[id=addTimestampCheck]:checked').map(function (index, el) {
                return $(this).val();
            });

            if (inputCheckBoxs.length == 0) {
                return false;
            }

            providerList = $('[id=provider]').map(function (index, el) {
                return $(this).val();
            });

            fileIdList = $('[id="file_id"]').map(function (index, el) {
                return $(this).val();
            });

            filePathList = $('[id=file_path]').map(function (index, el) {
                return $(this).val();
            });

            versionList = $('[id=version]').map(function (index, el) {
                return $(this).val();
            });

            fileNameList = $('[id=file_name]').map(function (index, el) {
                return $(this).val();
            });

            $("#btn-verify").attr("disabled", true);
            $("#btn-addtimestamp").attr("disabled", true);
            $("#timestamp_errors_spinner").text("Addtimestamp loading ...");
            errorFlg = false;
            successCnt = 0;
            for (var i = 0; i < inputCheckBoxs.length; i++) {
                 index = inputCheckBoxs[i];
                 var post_data = {'provider': providerList[index],
                                  'file_id': fileIdList[index],
                                  'file_path': filePathList[index],
                                  'file_name': fileNameList[index],
                                  'version': versionList[index]};
                 $.ajax({
                     beforeSend: function(){
                       $("#timestamp_errors_spinner").show();
                     },
                     url: nodeApiUrl + 'timestamp/add_timestamp/',
                     data: post_data,
                     dataType: 'json'
                 }).done(function(data) {
                     successCnt++;
                     $("#timestamp_errors_spinner").text("Adding Timestamp files : " + successCnt + " / " + inputCheckBoxs.length + " ...");
                     if (successCnt ==  inputCheckBoxs.length) {
                        $("#timestamp_errors_spinner").text("Added Timestamp (100%) and Refreshing...");
                        window.location.reload();
                     }
                 }).fail(function(xhr, textStatus, error) {
                    $("#btn-verify").removeAttr("disabled");
                    $("#btn-addtimestamp").removeAttr("disabled");
                    $("#timestamp_errors_spinner").text("Error : Timestamp Add Failed");
                    Raven.captureMessage('Timestamp Add Error: ' + filePathList[index], {
                        extra: {
                           url: url,
                           textStatus: textStatus,
                           error: error
                        }
                    });
                 });
            }
        };

        $('#addTimestampAllCheck').on('change', function() {
             $('input[id=addTimestampCheck]').prop('checked', this.checked);
        });

        var document_onready = function (event) {
            $("#btn-verify").on("click", btnVerify_onclick);
            $("#btn-addtimestamp").on("click", btnAddtimestamp_onclick).focus();
        };

        $(document).ready(document_onready);
        $("#timestamp_errors_spinner").hide();
     });
</script>
