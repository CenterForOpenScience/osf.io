<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/wiki-page.css">
</%def>
<!-- New Component Modal -->
<div class="modal fade" id="wikiImport">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">${_("Import wiki page")}</h3>
                </div><!-- end modal-header -->
                <div class="modal-body">
                    <div class='form-group'>
                        <select id="wikiImportDir" class="form-control">
                            % for import_dir in import_dirs:
                                <option value="${import_dir['id']}">${import_dir['name']}</option>
                            % endfor
                        </select>
                    </div>
                     <p class="text-danger wikiImportErrorMsg"> </p>
                </div><!-- end modal-body -->
                <div id="wikiImportFooter" class="modal-footer">
                    <button id="closeWikiImport" type="button" class="btn btn-default" data-dismiss="modal" style="display: none">${_("Close")}</button>
                    <button type="button" class="stopWikiImport btn btn-default" class="btn btn-default" style="display: none">${_("Stop import")}</button>
                    <button id="wikiImportSubmit" type="submit" class="btn btn-success">${_("Import")}</button>
                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<div class="modal fade" id="alertInfo">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">${_("Duplicate wiki name")}</h3>
                </div><!-- end modal-header -->
                <div class="modal-body" style="height: 550px;overflow: auto;">
                    <p id="attentionValidateInfo" class="partOperationAll" style="display: none">
                        ${_('The following wiki page already exists. Please select the process when importing. When creating a new wiki, the wiki name will be created with a sequential number like [Wiki name](1). If you dismiss this alert, the import will be aborted.')}
                    </p>
                     <p class="text-danger wikiImportErrorMsg"> </p>
                    <div class="partOperationAll" style="display: none">
                      <div class="importOperationItem"><input name="WikiImportOperation" type="radio" id="skipAll" value="skipAll" checked /><label for="skipAll">${_("Skip All")}</label></div>
                      <div class="importOperationItem"><input name="WikiImportOperation" type="radio" id="overwriteAll" value="overwriteAll"/><label for="overwriteAll">${_("Overwrite All")}</label></div>
                      <div class="importOperationItem"><input name="WikiImportOperation" type="radio" id="createNewAll" value="createNewAll"/><label for="createNewAll">${_("Create New All")}</label></div><br>
                    </div>
                    <div id="validateInfo" class="partOperationAll">
                        <ul></ul>
                    </div>
                    <p id="attentionDuplicatedInfo" style="display: none">
                        ${_('Duplicate wiki page name. The following pages will be registered as the Wiki page name listed.')}
                    </p>
                    <div id="duplicatedInfo" class="partOperationAll">
                        <ul></ul>
                    </div>
                    <div id="perFileDifinitionForm" style="display: none">
                        <ul></ul>
                    </div>
                    <p id="attentionDuplicatedFolder" style="display: none">
                        ${_('The following folder are duplicated in the import directory.')}
                    </p>
                    <div id="duplicatedFolder">
                        <ul></ul>
                    </div>
                </div><!-- end modal-body -->
                <div class="modal-footer">
                    <button type="button" class="stopWikiImport btn btn-default" class="btn btn-default" style="display: none">${_("Stop import")}</button>
                    <button id="backalertInfo" type="button" class="btn btn-default btnIndividual" style="display: none">${_("Back")}</button>
                    <button id="closeAlertInfo" type="button" class="btn btn-default" data-dismiss="modal" style="display: none">${_("Close")}</button>
                    <button id="continueWikiImportSubmit" type="submit" class="btn btn-success btnAll btnIndividual" style="display: none">${_("Continue import")}</button>
                    <button id="perFileDefinition" type="button" class="btn btn-warning btnAll" style="display: none">${_("Per-file definition")}</button>
                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<div class="modal fade" id="wikiImportResult">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h3 class="modal-title">${_("Import Result")}</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                <div id="showWikiImportError" style="display: none">
                </div>
            </div><!-- end modal-body -->
            <div class="modal-footer">
                <a href="#" class="btn btn-success" data-dismiss="modal" >${_("OK")}</a>
            </div><!-- end modal-footer -->
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script type="text/javascript">
    $(function () {
        var $wikiImportForm = $('#wikiImport form');
        var $alertInfoForm = $('#alertInfo form');
        var $wikiImportResult = $('#wikiImportResult')
        var $wikiImportErrorMsg = $('.wikiImportErrorMsg');
        var selectOperation = '<div class="form-group" name="WikiImportOperationPer"><select class="form-control" name="WikiImportOperationPerSelect"><option value="skip">${_("Skip")}</option><option value="overwrite">${_("Overwrite")}</option><option value="createNew">${_("Create New")}</option></select></div>'
        var validateWikiImportResultData = [];
        var wikiImportErrors = [];
        const VALIDATE_WIKI_IMPORT_INTERVAL = 1000;
        const VALIDATE_N = 300
        const VALIDATE_WIKI_IMPORT_TIMEOUT = VALIDATE_WIKI_IMPORT_INTERVAL * VALIDATE_N;
        const WIKI_IMPORT_INTERVAL = 5000;
        const IMPORT_N = 1440;
        const WIKI_IMPORT_TIMEOUT = WIKI_IMPORT_INTERVAL * IMPORT_N;
        const WIKI_IMPORT_OPERATION = 'import';
        const VALIDATE_WIKI_IMPORT_OPERATION = 'validate';

        $wikiImportForm.on('submit', async function (e) {
            e.preventDefault();
            // Clean
            wikiImportErrors = [];
            validateWikiImportResultData = [];
            const $wikiImportDir = $wikiImportForm.find('#wikiImportDir');
            const $submitForm = $wikiImportForm.find('#wikiImportSubmit');
            const $stopWikiImport = $wikiImportForm.find('.stopWikiImport');
            const dirId = $wikiImportDir.val();
            const validateWikiImportUrl = ${ urls['api']['base'] | sjson, n } + 'import/' + dirId + '/validate/';
            const validateWikiImportTask = await requestvalidateWikiImportTask(validateWikiImportUrl, $alertInfoForm, $submitForm);
            const taskId = validateWikiImportTask.taskId;
            $submitForm.attr('disabled', 'disabled').text('${_("Validating wiki pages")}');
            const getTaskResultUrl = ${ urls['api']['base'] | sjson, n } + 'get_task_result/' + taskId+ '/';
            const validateWikiImportResult = await intervalGetCeleryTaskResult(getTaskResultUrl, VALIDATE_WIKI_IMPORT_INTERVAL, VALIDATE_WIKI_IMPORT_TIMEOUT, 'validate')
            if (validateWikiImportResult) {
                if (validateWikiImportResult.canStartImport) {
                    var data = modifyImportList('', validateWikiImportResult.data)
                    startWikiImport(data, dirId, $submitForm, $stopWikiImport);
                } else {
                    showAlertInfo(validateWikiImportResult, $alertInfoForm);
                    $submitForm.attr('disabled', false).text('${_("Import")}');
                }
            }
            return;
        });

        $alertInfoForm.on('submit', function (e) {
            e.preventDefault();
            const $wikiImportDir = $wikiImportForm.find('#wikiImportDir');
            const $submitForm = $alertInfoForm.find('#continueWikiImportSubmit');
            const $perFile = $alertInfoForm.find('#perFileDefinition');
            const $perBack = $alertInfoForm.find('#backalertInfo');
            const $stopWikiImport = $alertInfoForm.find('.stopWikiImport');
            var operationAll = null;
            var perOperationList = []
            var perFileDifinitionFormDisplay = document.getElementById('perFileDifinitionForm').style.display;
            if (perFileDifinitionFormDisplay === 'none') {
                var WikiImportOperations = document.getElementsByName('WikiImportOperation');
                for (var i = 0; i < WikiImportOperations.length; i++){
                    if (WikiImportOperations.item(i).checked) {
                        operationAll = WikiImportOperations.item(i).value;
                    }
                }
            } else if (perFileDifinitionFormDisplay === '') {
                var $perFileList = $('#perFileDifinitionForm li');
                for (var j = 0; j < $perFileList.length; j++){
                    var wiki_name = ($perFileList[j].id).substring(($perFileList[j].id).lastIndexOf('/') + 1);
                    var operation = $perFileList[j].children.WikiImportOperationPer.children.WikiImportOperationPerSelect.value;
                    var opList = { wiki_name: wiki_name, operation: operation};
                    perOperationList.push(opList);
                }
            }
            var validateWikiImportResultCopy = validateWikiImportResultData.slice();
            var validateWikiImportResultFix = modifyImportList(operationAll, validateWikiImportResultCopy, perOperationList);
            if (validateWikiImportResultFix.length === 0) {
                alert('${_("No page to import")}');
            } else {
                var dirId = $wikiImportDir.val();
                $perFile.attr('disabled', 'disabled');
                $perBack.attr('disabled', 'disabled');
                startWikiImport(validateWikiImportResultFix, dirId, $submitForm, $stopWikiImport);
            }
            return;
        });

        async function startWikiImport(data, dirId, $submitForm, $stopWikiImport) {
            var wikiImportUrl = ${ urls['api']['base'] | sjson, n } + 'import/' + dirId + '/';
            var wikiImportTask = await requestWikiImportTask(wikiImportUrl, data);
            var taskId = wikiImportTask.taskId;
            // show stop import Btn
            $stopWikiImport.css('display', '');
            //change import label
            $submitForm.attr('disabled', 'disabled').text('${_("Importing Wiki...")}');
            var getTaskResultUrl = ${ urls['api']['base'] | sjson, n } + 'get_task_result/' + taskId + '/';
            wikiImportResult = await intervalGetCeleryTaskResult(getTaskResultUrl, WIKI_IMPORT_INTERVAL, WIKI_IMPORT_TIMEOUT, 'import');
            if (wikiImportResult) {
                // The series of import processes has reached the end.
                if ((wikiImportResult.import_errors).length > 0) {
                    showErrModal($wikiImportResult, $alertInfoForm);
                } else {
                    $submitForm.attr('disabled', 'disabled').text('${_("Import Complete")}');
                    //reload
                    const reloadUrl = (location.href).replace(location.search, '')
                    window.location.assign(reloadUrl);
                }
            }
            return;
        }
        /**
         * Modifies the import list based on the specified operation.
         *
         * @param {string} operation - Specifies the operation to perform. Can be 'skipAll', 'overwriteAll', 'createNewAll', or an empty string.
         * @param {Array} validateWikiImportResultCopy - Copy of the import list. The modified list will be returned.
         * @param {Array} perOperationList - List of operations for each item.
         * @returns {Array} The modified import list.
         */
        function modifyImportList(operation, validateWikiImportResultCopy, perOperationList) {
            if (operation === null && perOperationList.length > 0) {
                return validateWikiImportResultCopy.filter(item => {
                    if (item.status === 'invalid') {
                        return false;
                    }

                    const perOperation = perOperationList.find(op => op.wiki_name === item.wiki_name);
                    if (!perOperation) {
                        return true;
                    }

                    switch (perOperation.operation) {
                        case 'skip':
                            return false;
                        case 'overwrite':
                            return true;
                        case 'createNew':
                            if (item.status === 'valid_exists') {
                                item.wiki_name +=  '(' + item.numbering + ')';
                                item.path += '(' + item.numbering + ')';
                            }
                            return true;
                        default:
                            return true;
                    }
                });
            } else if (operation === 'skipAll' || operation === '') {
                return validateWikiImportResultCopy.filter(item => item.status === 'valid' || item.status === 'valid_duplicated');
            } else if (operation === 'overwriteAll') {
                return validateWikiImportResultCopy.filter(item => item.status !== 'invalid');
            } else if (operation === 'createNewAll') {
                return validateWikiImportResultCopy.map(item => {
                    if (item.status === 'invalid') {
                        return null;
                    } else if (item.status === 'valid_exists') {
                        return {
                            ...item,
                            wiki_name: item.wiki_name + '(' + item.numbering + ')',
                            path: item.path + '(' + item.numbering + ')'
                        };
                    } else {
                        return item;
                    }
                }).filter(Boolean);
            } else {
                // Default: Same as 'skipAll'
                return validateWikiImportResultCopy.filter(item => item.status === 'valid' || item.status === 'valid_duplicated');
            }
        }

        function showAlertInfo(validateWikiImportResult, $alertInfoForm) {
            $('#alertInfo').modal('show');
            $('#wikiImport').modal('hide');
            showAlertInfoBtn();
            if (validateWikiImportResult.duplicated_folder.length > 0) {
                // show duplicated folder sentence
                $('#attentionDuplicatedFolder').css('display', '');
                // show Close Btn
                $('#closeAlertInfo').css('display', '');
                // hide the display of operations for all
                $alertInfoForm.find('.partOperationAll').css('display', 'none');
                // show duplicated import folder list
                validateWikiImportResult.duplicated_folder.forEach(function(item) {
                    $('#duplicatedFolder ul').append('<li>' + item + '</li>');
                });
            } else {
                validateWikiImportResultData = validateWikiImportResult.data;
                // show the Btn of operations for all
                $('.btnAll').css('display', '');
                // show duplicated wiki page infomation
                var valid_exists_ctn = 0;
                validateWikiImportResultData.forEach(function(item) {
                    if (item.status === 'valid_exists') {
                        valid_exists_ctn++;
                        $alertInfoForm.find('.partOperationAll').css('display', '');
                        $('#validateInfo ul').append('<li>' + (item.path).slice(1) + '</li>')
                        $('#perFileDifinitionForm ul').append('<li id="' + (item.path).slice(1) + '" name="WikiImportOperationPerItem">' + '<div name="WikiImportOperationPerName">' +  (item.path).slice(1) + '</div>' + selectOperation + '</li>');
                    } else if (item.status === 'valid_duplicated'){
                        $('#attentionDuplicatedInfo').css('display', '');
                        $('#duplicatedInfo ul').append('<li>' + (item.path).slice(1) + '</li>')
                    }
                });
                if (valid_exists_ctn === 0) {
                    document.getElementById("perFileDefinition").style.display = "none";
                }
            }
        }

        async function requestvalidateWikiImportTask(url, $alertInfoForm, $submitForm) {
            await new Promise(function(resolve){
                result = validateWikiImportTaskPromise(url, $alertInfoForm, $submitForm)
                resolve();
            });
            return result
        }

        async function validateWikiImportTaskPromise(url, $alertInfoForm, $submitForm) {
            return $.ajax({
                type: 'GET',
                cache: false,
                url: url,
                dataType: 'json'
            }).fail(function (response) {
                if (response.status !== 0) {
                    $wikiImportErrorMsg.text(response.status + ' : Error occurred when wiki validate.');
                }
            });
        }

        async function requestWikiImportTask(wikiImportUrl, data) {
            await new Promise(function(resolve){
                result = wikiImportTaskPromise(wikiImportUrl, data)
                resolve();
            });
            return result
        }

        async function wikiImportTaskPromise(wikiImportUrl, data) {
            return $.ajax({
                type: 'POST',
                cache: false,
                url: wikiImportUrl,
                data: JSON.stringify(data),
                contentType: 'application/json; charset=utf-8',
            }).fail(function (response) {
                if (response.status !== 0) {
                    dispBtnWhenError();
                    if (response.responseJSON) {
                        $wikiImportErrorMsg.text(response.responseJSON.message_long);
                    } else {
                        $wikiImportErrorMsg.text('Error occurred when wiki import.');
                    }
                }
            });
        }

        function showErrModal($wikiImportResult, $alertInfoForm) {
            // show import error modal.
            wikiImportErrors.push(...wikiImportResult.import_errors)
            var wikiImportErrorMsg = createErrMsg(wikiImportErrors);
            $('#wikiImport').modal('hide');
            $('#alertInfo').modal('hide');
            $('#wikiImportResult').modal('show');
            $('#showWikiImportError').append('<p>' + wikiImportErrorMsg + '</p>')
            $wikiImportResult.find('#showWikiImportError').css('display', '');
            $alertInfoForm.find('.btnAll').css('display', 'none');
        }

        function createErrMsg(errorList) {
            var errMsg = 'The following wiki pages could not be imported.';
            for (var i = 0; i < errorList.length; i++) {
                errMsg += '<br>' + errorList[i];
            }
            return errMsg;
        }

        async function intervalGetCeleryTaskResult(url, interval_ms, timeout_ms, operation) {
            var count = 0;
            var result = '';
            var timeoutCtn = Math.ceil(timeout_ms / interval_ms);
            while (count < timeoutCtn) {
                result = await getCeleryTaskResult(url, operation)
                if (result) {
                    if(result.aborted) {
                        alert('${_("Wiki import aborted.")}');
                        dispBtnWhenAbort();
                        $('#wikiImport').modal('hide');
                        $('#alertInfo').modal('hide');
                    }
                    break;
                }
                await new Promise(function(resolve){
                    setTimeout(resolve, interval_ms);
                });
                count++;
            }
            if (count === timeoutCtn){
                if (operation === WIKI_IMPORT_OPERATION) {
                    alert('${_("The request has timed out, but the process is still ongoing. Processing may take longer if there are many pages. Please reload the page to check the import result. If the process takes too long, we recommend contacting support or trying again later.")}')
                } else if (operation === VALIDATE_WIKI_IMPORT_OPERATION) {
                    alert('${_("The response has timed out. High server load may cause delays in processing. Please try again. If the issue persists, please contact support.")}')
                }
                return;
            }
            return result;
        }

        async function getCeleryTaskResult(getCeleryTaskUrl, operation) {
            return $.ajax({
                type: 'GET',
                cache: false,
                url: getCeleryTaskUrl,
                dataType: 'json',
            }).fail(function (response) {
                if (response.status !== 0) {
                    dispBtnWhenError();
                    if (response.responseJSON) {
                        if (response.responseJSON.message_long) {
                            $wikiImportErrorMsg.text(response.responseJSON.message_long);
                        } else {
                            alert('${_("import error")}');
                        }
                    } else {
                        alert('${_("import error")}');
                    }
                    return;
                }
            });
        }

        function cleanCeleryTask() {
            var cleanTasksUrl = ${ urls['api']['base'] | sjson, n } + 'tasks/clean/';
            $.ajax({
                type: 'POST',
                cache: false,
                url: cleanTasksUrl,
                dataType: 'json',
            })
        }

        $alertInfoForm.find('#perFileDefinition').on('click', function () {
            showPerFileDefinition();
        });
        $alertInfoForm.find('#backalertInfo').on('click', function () {
            backalertInfo();
        });
        $('#alertInfo').on('hidden.bs.modal', function (event) {
            $('#alertInfo li').remove();
        });
        $alertInfoForm.find('.stopWikiImport').on('click', function () {
            cleanCeleryTask();
            $alertInfoForm.find('.stopWikiImport').css('display', 'none');
            $alertInfoForm.find('#continueWikiImportSubmit').attr('disabled', 'disabled').text('${_("Aborting...")}');
        });
        $wikiImportForm.find('.stopWikiImport').on('click', function () {
            $wikiImportForm.find('.stopWikiImport').css('display', 'none');
            $wikiImportForm.find('#wikiImportSubmit').attr('disabled', 'disabled').text('${_("Aborting...")}');
            cleanCeleryTask();
        });
        $('#wikiImport').on('show.bs.modal', function () {
            showWikiImportBtn();
        });

        function showWikiImportBtn() {
            $wikiImportForm.find('#wikiImportSubmit').attr('disabled', false).css('display', '').text('${_("Import")}');
            $wikiImportForm.find('#closeWikiImport').css('display', 'none');
            $wikiImportErrorMsg.text('');
        }
        function showPerFileDefinition() {
            $alertInfoForm.find('.partOperationAll').css('display', 'none');
            $alertInfoForm.find('.btnAll').css('display', 'none');
            $alertInfoForm.find('.btnIndividual').css('display', '');
            $alertInfoForm.find('#perFileDifinitionForm').css('display', '');
        }
        function showAlertInfoBtn() {
            $alertInfoForm.find('#continueWikiImportSubmit').attr('disabled', false).css('display', '').text('${_("Import")}');;
            $alertInfoForm.find('#perFileDefinition').attr('disabled', false).css('display', '');
            $alertInfoForm.find('#closeAlertInfo').css('display', 'none');
            $alertInfoForm.find('#backalertInfo').css('display', 'none');
        }
        function backalertInfo() {
            $alertInfoForm.find('#perFileDifinitionForm').css('display', 'none');
            $alertInfoForm.find('.partOperationAll').css('display', '');
            $alertInfoForm.find('.btnIndividual').css('display', 'none');
            $alertInfoForm.find('.btnAll').attr('disabled', false).css('display', '');
        }
        function dispBtnWhenError() {
            $alertInfoForm.find('#closeAlertInfo').attr('disabled', false).css('display', '');
            $wikiImportForm.find('#closeWikiImport').css('display', '');
            $wikiImportForm.find('.stopWikiImport').css('display', 'none');
            $alertInfoForm.find('.stopWikiImport').css('display', 'none');
            $alertInfoForm.find('#continueWikiImportSubmit').css('display', 'none');
            $wikiImportForm.find('#wikiImportSubmit').css('display', 'none');
            $alertInfoForm.find('#perFileDefinition').css('display', 'none');
            $alertInfoForm.find('#backalertInfo').css('display', 'none');
        }
        function dispBtnWhenAbort() {
            $alertInfoForm.find('#continueWikiImportSubmit').attr('disabled', false).text('${_("Import")}');
            $wikiImportForm.find('#wikiImportSubmit').attr('disabled', false).text('${_("Import")}');
            $wikiImportForm.find('.stopWikiImport').css('display', 'none');
            $alertInfoForm.find('.stopWikiImport').css('display', 'none');
            $alertInfoForm.find('.btnAll').attr('disabled', false).css('display', '');
            $alertInfoForm.find('.btnIndividual').attr('disabled', false).css('display', '');
        }
    });
</script>
