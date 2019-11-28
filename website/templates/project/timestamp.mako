<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} ${_("Timestamp")}</%def>

<div class="page-header  visible-xs">
    <h2 class="text-300">Timestamp</h2>
</div>

<div class="row">
    <div class="col-sm-5">
        <h2 class="break-word">${_("Timestamp Control")}</h2>
    </div>
    <div class="col-sm-7">
        <div id="toggleBar" class="pull-right"></div>
    </div>
</div>

<hr/>

<div class="row project-page">

    <!-- Begin left column -->
    <div class="col-md-3 col-xs-12 affix-parent scrollspy">
        <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="105" data-offset-bottom="263">
            <!-- Begin sidebar -->
            <ul class="nav nav-stacked nav-pills">
                <li class="active">
                    <a href="#">${_("Timestamp Error")}</a>
                </li>
            </ul>
        </div>
    </div>

    <div class="col-md-9 col-xs-12">
        <div id="timestamp-form" class="form">
            <div class="row">
                <div class="col-xl-8 col-lg-10 col-sm-12">
                    <form>
                        <div class="form-group row">
                            <div class="col-sm-6">
                                <div class="input-group">
                                    <div class="input-group-addon">${_("Start Date")}</div>
                                    <input id="startDateFilter" type="text" placeholder="YYYY-MM-DD" class="form-control" />
                                </div>
                            </div>
                            <div class="col-sm-6">
                                <div class="input-group">
                                    <div class="input-group-addon">${_("End Date")}</div>
                                    <input id="endDateFilter" type="text" placeholder="YYYY-MM-DD" class="form-control" />
                                </div>
                            </div>
                            <div class="col-sm-6">
                                <div class="input-group">
                                    <div class="input-group-addon">${_("User")}</div>
                                    <select id="userFilterSelect" class="form-control">
                                        <option value=""></option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-sm-12">
                                <button type="button" class="btn btn-primary" id="applyFiltersButton">${_("Apply")}</button>
                            </div>
                        </div>
                    </form>
                </div>
                <div class="col-sm-12" style="margin-bottom: 10px;">
                    <div class="row">
                        <div class="col-sm-7">
                            <span>
                                <button type="button" class="btn btn-success" id="btn-verify" ${ 'disabled=disabled' if not async_task['ready'] else '' }>${_("Verify")}</button>
                                <button type="button" class="btn btn-success" id="btn-addtimestamp" ${ 'disabled=disabled' if not async_task['ready'] else '' }>${_("Request Trusted Timestamp")}</button>
                                <button type="button" class="btn btn-default" id="btn-cancel" ${ 'disabled=disabled' if async_task['ready'] else '' }>${_("Cancel")}</button>
                            </span>
                        </div>
                        <div class="col-sm-5"></div>
                    </div>
                </div>
            </div>
            <div class="row" id="loading-row" style="${ 'display: none;' if async_task['ready'] else '' }">
                <div class="col-xs-12">
                    <div class="spinner-loading-wrapper">
                        <p class="m-t-sm fg-load-message" id="loading-message">${_("Processing, please wait...")}</p>
                        <div class="logo-spin logo-lg"></div>
                    </div>
                </div>
            </div>
            <div class="row" id="pagination-row" style="${ 'display: none;' if not async_task['ready'] else '' }">
                <div class="col-sm-8">
                    <ul class="pagination-wrap" style="display: none;">
                        <li class="pagination-prev">
                            <a class="page">&#060;</a>
                        </li>
                        <ul class="listjs-pagination"></ul>
                        <li class="pagination-next">
                            <a class="page">&#062;</a>
                        </li>
                    </ul>
                </div>
                <div class="col-sm-2">
                    <label class="pull-right" style="margin: 20px 0;">${_("per page:")}</label>
                </div>
                <div class="col-sm-2">
                    <select id="pageLength" class="form-control" style="margin: 15px 0;">
                        <option value="10">10</option>
                        <option value="20">20</option>
                        <option value="30">30</option>
                    </select>
                </div>
            </div>
            <div class="row" id="timestamp-table-row" style="${ 'display: none;' if not async_task['ready'] else '' }">
                <div class="col-xs-12">
                    <table class="table table-bordered table-addon-terms">
                        <thead class="block-head">
                            <tr style="background-color: #f5f5f5;">
                                <th width="3%">
                                    <input type="checkBox" id="addTimestampAllCheck" style="width: 15px; height: 15px;"/>
                                </th>
                                <th width="14%">
                                    <span class="sorter">
                                        <i id="sort_up_provider" class="fa fa-chevron-up tb-sort-inactive asc-btn m-r-xs"></i>
                                        <i id="sort_down_provider" class="fa fa-chevron-down tb-sort-inactive desc-btn"></i>
                                    </span>
                                    <span class="header_text m-r-sm" title="Provider">${_("Provider")}</span>
                                </th>
                                <th width="29%">
                                    <span class="sorter">
                                        <i id="sort_up_file_path" class="fa fa-chevron-up tb-sort-inactive asc-btn m-r-xs"></i>
                                        <i id="sort_down_file_path" class="fa fa-chevron-down tb-sort-inactive desc-btn"></i>
                                    </span>
                                    <span class="header_text m-r-sm" title="File Path">${_("File Path")}</span>
                                </th>
                                <th width="15%">
                                    <span class="sorter">
                                        <i id="sort_up_verify_user_name_id" class="fa fa-chevron-up tb-sort-inactive asc-btn m-r-xs"></i>
                                        <i id="sort_down_verify_user_name_id" class="fa fa-chevron-down tb-sort-inactive desc-btn"></i>
                                    </span>
                                    <span class="header_text m-r-sm" title="Timestamp by">${_("Timestamp by")}</span>
                                </th>
                                <th width="19%">
                                    <span class="sorter">
                                        <i id="sort_up_verify_date" class="fa fa-chevron-up tb-sort-inactive asc-btn m-r-xs"></i>
                                        <i id="sort_down_verify_date" class="fa fa-chevron-down tb-sort-inactive desc-btn"></i>
                                    </span>
                                    <span class="header_text m-r-sm" title="Updated at">${_("Updated at")}</span>
                                </th>
                                <th width="20%">
                                    <span class="sorter">
                                        <i id="sort_up_verify_result_title" class="fa fa-chevron-up tb-sort-inactive asc-btn m-r-xs"></i>
                                        <i id="sort_down_verify_result_title" class="fa fa-chevron-down tb-sort-inactive desc-btn"></i>
                                    </span>
                                    <span class="header_text m-r-sm" title="Timestamp Verification">${_("Timestamp Verification")}</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody class="list" id="timestamp_error_list">
                            % for provider_error_info in provider_list:
                                % for error_info in provider_error_info['error_list']:
                                <tr class="addTimestamp">
                                    <td>
                                        <input type="checkBox" id="addTimestampCheck" style="width: 15px; height: 15px;"/>
                                    </td>
                                    <td class="provider">${ provider_error_info['provider'] }</td>
                                    <td>${ error_info['file_path'] }</td>

                                    <input type="hidden" class="creator_name" value="${ error_info['creator_name'] }" />
                                    <input type="hidden" class="creator_email" value="${ error_info['creator_email'] }" />
                                    <input type="hidden" class="creator_id" value="${ error_info['creator_id'] }" />
                                    <input type="hidden" class="file_path" value="${ error_info['file_path'] }" />
                                    <input type="hidden" class="file_id" value="${ error_info['file_id'] }" />
                                    <input type="hidden" class="file_create_date_on_upload" value="${ error_info['file_create_date_on_upload'] }" />
                                    <input type="hidden" class="file_create_date_on_verify" value="${ error_info['file_create_date_on_verify'] }" />
                                    <input type="hidden" class="file_modify_date_on_upload" value="${ error_info['file_modify_date_on_upload'] }" />
                                    <input type="hidden" class="file_modify_date_on_verify" value="${ error_info['file_modify_date_on_verify'] }" />
                                    <input type="hidden" class="file_size_on_upload" value="${ error_info['file_size_on_upload'] }" />
                                    <input type="hidden" class="file_size_on_verify" value="${ error_info['file_size_on_verify'] }" />
                                    <input type="hidden" class="file_version" value="${ error_info['file_version'] }" />
                                    <input type="hidden" class="project_id" value="${ error_info['project_id'] }" />
                                    <input type="hidden" class="organization_id" value="${ error_info['organization_id'] }" />
                                    <input type="hidden" class="organization_name" value="${ error_info['organization_name'] }" />
                                    <input type="hidden" class="verify_user_id" value="${ error_info['verify_user_id'] }" />
                                    <input type="hidden" class="verify_user_name" value="${ error_info['verify_user_name'] }" />
                                    <input type="hidden" class="verify_date" value="${ error_info['verify_date'] }" />
                                    <input type="hidden" class="verify_result_title" value="${ error_info['verify_result_title'] }" />

                                    <td class="verify_user_name_id">${ u'{} ({})'.format(error_info['verify_user_name'], error_info['verify_user_id']) if error_info['verify_user_id'] else 'Unknown' }</td>
                                    <td class="verify_date" style="color: white;">${ error_info['verify_date'] if error_info['verify_date'] else 'Unknown' }</td>
                                    <td class="verify_result_title">${ error_info['verify_result_title'] }</td>
                                </tr>
                                % endfor
                            % endfor
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="row" id="download-row" style="${ 'display: none;' if not async_task['ready'] else '' }">
                <div class="col-sm-3">
                    <span>
                        <select id="fileFormat" class="form-control">
                            <option value="csv">CSV</option>
                            <option value="json-ld">JSON/LD</option>
                            <option value="rdf-xml">RDF/XML</option>
                        </select>
                    </span>
                </div>
                <div class="col-sm-2">
                    <span>
                        <button type="button" class="btn btn-success" id="btn-download">${_("Download")}</button>
                    </span>
                </div>
                <div class="col-sm-7"></div>
            </div>
        </div>
    </div>
</div>

<link href="/static/css/pages/timestamp-page.css" rel="stylesheet" />
<link href="https://cdnjs.cloudflare.com/ajax/libs/tiny-date-picker/3.2.8/tiny-date-picker.min.css" rel="stylesheet" />

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
% for script in tree_js:
<script type="text/javascript" src="${script | webpack_asset}"></script>
% endfor
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/tiny-date-picker/3.2.8/tiny-date-picker.min.js"></script>
<script src=${"/static/public/js/timestamp-page.js" | webpack_asset}></script>
</%def>
