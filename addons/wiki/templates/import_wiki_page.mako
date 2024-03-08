<!-- New Component Modal -->
<div class="modal fade" id="importWiki">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">${_("Import wiki page")}</h3>
                </div><!-- end modal-header -->
                <div class="modal-body">
                    <div class='form-group'>
                        <select id="importDir" class="form-control">
                            % for import_dir in import_dirs:
                                <option value="${import_dir['id']}">${import_dir['name']}</option>
                            % endfor
                        </select>
                    </div>
                     <p class="text-danger importErrorMsg"> </p>
                </div><!-- end modal-body -->
                <div id="importFooter" class="modal-footer">
                    <button id="closeImport" type="button" class="btn btn-default" data-dismiss="modal" style="display: none">${_("Close")}</button>
                    <button type="button" class="stopImport btn btn-default" class="btn btn-default" style="display: none">${_("Stop import")}</button>
                    <button id="importWikiSubmit" type="submit" class="btn btn-success">${_("Import")}</button>
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
                     <p class="text-danger importErrorMsg"> </p>
                    <div class="partOperationAll" style="display: none">
                      <div style="display: inline-block; margin-right: 10px;"><input name="importOperation" type="radio" id="skipAll" value="skipAll" checked /><label for="skipAll">Skip All</label></div>
                      <div style="display: inline-block; margin-right: 10px;"><input name="importOperation" type="radio" id="overwriteAll" value="overwriteAll"/><label for="overwriteAll">Overwrite All</label></div>
                      <div style="display: inline-block; margin-right: 10px;"><input name="importOperation" type="radio" id="createNewAll" value="createNewAll"/><label for="createNewAll">Create New All</label></div><br>
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
                    <button type="button" class="stopImport btn btn-default" class="btn btn-default" style="display: none">${_("Stop import")}</button>
                    <button id="backalertInfo" type="button" class="btn btn-default btnIndividual" style="display: none">${_("Back")}</button>
                    <button id="closeAlertInfo" type="button" class="btn btn-default" data-dismiss="modal" style="display: none">${_("Close")}</button>
                    <button id="continueImportWikiSubmit" type="submit" class="btn btn-success btnAll btnIndividual" style="display: none">${_("Continue import")}</button>
                    <button id="perFileDefinition" type="button" class="btn btn-warning btnAll" style="display: none">${_("Per-file definition")}</button>
                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<div class="modal fade" id="importResult">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h3 class="modal-title">${_("Import Result")}</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                <div id="showImportError" style="display: none">
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
        var $importWikiForm = $('#importWiki form');
        var $alertInfoForm = $('#alertInfo form');
        var $importResult = $('#importResult')
        var $importErrorMsg = $('.importErrorMsg');
        var selectOperation = '<div class="form-group" name="importOperationPer" style="display: inline-block; margin-left: 10px;"><select class="form-control" name="importOperationPerSelect"><option value="skip">Skip</option><option value="overwrite">Overwrite</option><option value="createNew">Create New</option></select></div>'
        var validateImportResultData = [];
        var importErrors = [];
        const VALIDATE_IMPORT_TIMEOUT = 300;
        const WIKI_IMPORT_TIMEOUT = 7200;

        $importWikiForm.on('submit', async function (e) {
            e.preventDefault();
            // Clean
            importErrors = [];
            validateImportResultData = [];
            const $importDir = $importWikiForm.find('#importDir');
            const $submitForm = $importWikiForm.find('#importWikiSubmit');
            const $stopImport = $importWikiForm.find('.stopImport');
            const dirId = $importDir.val();
            const validateImportUrl = ${ urls['api']['base'] | sjson, n } + 'import/' + dirId + '/validate/';
            const validateImportTask = await requestValidateImportTask(validateImportUrl, $alertInfoForm, $submitForm);
            const taskId = validateImportTask.taskId;
            $submitForm.attr('disabled', 'disabled').text('${_("Validating wiki pages")}');
            const getTaskResultUrl = ${ urls['api']['base'] | sjson, n } + 'get_task_result/' + taskId+ '/';
            const validateImportResult = await intervalGetCeleryTaskResult(getTaskResultUrl, 1000, VALIDATE_IMPORT_TIMEOUT, 'validate wiki pages')
            if (validateImportResult) {
                if (validateImportResult.canStartImport) {
                    var data = fixToImportList('', validateImportResult.data)
                    startImportWiki(data, dirId, $submitForm, $stopImport);
                } else {
                    showAlertInfo(validateImportResult, $alertInfoForm);
                    $submitForm.attr('disabled', false).text('${_("Import")}');
                }
            }
            return;
        });

        $alertInfoForm.on('submit', function (e) {
            e.preventDefault();
            const $importDir = $importWikiForm.find('#importDir');
            const $submitForm = $alertInfoForm.find('#continueImportWikiSubmit');
            const $perFile = $alertInfoForm.find('#perFileDefinition');
            const $perBack = $alertInfoForm.find('#backalertInfo');
            const $stopImport = $alertInfoForm.find('.stopImport');
            var operationAll = null;
            var perOperationList = []
            var perFileDifinitionFormDisplay = document.getElementById('perFileDifinitionForm').style.display;
            if (perFileDifinitionFormDisplay === 'none') {
                var importOperations = document.getElementsByName('importOperation');
                for (var i = 0; i < importOperations.length; i++){
                    if (importOperations.item(i).checked) {
                        operationAll = importOperations.item(i).value;
                    }
                }
            } else if (perFileDifinitionFormDisplay === '') {
                var $perFileList = $('#perFileDifinitionForm li');
                for (var j = 0; j < $perFileList.length; j++){
                    var wiki_name = ($perFileList[j].id).substring(($perFileList[j].id).lastIndexOf('/') + 1);
                    var operation = $perFileList[j].children.importOperationPer.children.importOperationPerSelect.value;
                    var opList = { wiki_name: wiki_name, operation: operation};
                    perOperationList.push(opList);
                }
            }
            var validateImportResultCopy = validateImportResultData.slice();
            var validateImportResultFix = fixToImportList(operationAll, validateImportResultCopy, perOperationList);
            if (validateImportResultFix.length === 0) {
                alert('No page to import.');
            } else {
                var dirId = $importDir.val();
                $perFile.attr('disabled', 'disabled');
                $perBack.attr('disabled', 'disabled');
                startImportWiki(validateImportResultFix, dirId, $submitForm, $stopImport);
            }
            return;
        });

        async function startImportWiki(data, dirId, $submitForm, $stopImport) {
            var wikiImportUrl = ${ urls['api']['base'] | sjson, n } + 'import/' + dirId + '/';
            var wikiImportTask = await requestWikiImportTask(wikiImportUrl, data);
            var taskId = wikiImportTask.taskId;
            // show stop import Btn
            $stopImport.css('display', '');
            //change import label
            $submitForm.attr('disabled', 'disabled').text('${_("Importing Wiki...")}');
            var getTaskResultUrl = ${ urls['api']['base'] | sjson, n } + 'get_task_result/' + taskId + '/';
            wikiImportResult = await intervalGetCeleryTaskResult(getTaskResultUrl, 5000, WIKI_IMPORT_TIMEOUT, 'import wiki');
            if (wikiImportResult) {
                // The series of import processes has reached the end.
                if ((wikiImportResult.import_errors).length > 0) {
                    showErrModal($importResult, $alertInfoForm);
                } else {
                    $submitForm.attr('disabled', 'disabled').text('${_("Import Complete")}');
                    //reload
                    const reloadUrl = (location.href).replace(location.search, '')
                    window.location.assign(reloadUrl);
                }
            }
            return;
        }

        function fixToImportList(operation, validateImportResultCopy, perOperationList) {
            if (operation === null && perOperationList.length > 0) {
                for (var m=validateImportResultCopy.length-1; m>=0; m--) {
                    if (validateImportResultCopy[m].status === 'invalid') {
                        validateImportResultCopy.splice(m, 1);
                        continue;
                    }
                    for (var n=0; n<perOperationList.length; n++) {
                        if (validateImportResultCopy[m].wiki_name === perOperationList[n].wiki_name) {
                            if (perOperationList[n].operation === 'skip') {
                                validateImportResultCopy.splice(m, 1);
                                break;
                            } else if (perOperationList[n].operation === 'overwrite') {
                                break;
                                // no deal
                            } else if (perOperationList[n].operation === 'createNew') {
                                if ((validateImportResultCopy[m].status).startsWith('valid_')){
                                    validateImportResultCopy[m].wiki_name = validateImportResultCopy[m].wiki_name + '(' + validateImportResultCopy[m].numbering + ')';
                                    validateImportResultCopy[m].path = validateImportResultCopy[m].path + '(' + validateImportResultCopy[m].numbering + ')';
                                }
                                break;
                            }
                        }
                    }
                }
            } else if (operation === 'skipAll' || operation === '') {
                for (var i=validateImportResultCopy.length-1; i>=0; i--) {
                    if (validateImportResultCopy[i].status !== 'valid' && validateImportResultCopy[i].status !== 'valid_duplicated') {
                        validateImportResultCopy.splice(i, 1);
                    }
                }
            } else if (operation === 'overwriteAll') {
                for (var j=validateImportResultCopy.length-1; j>=0; j--) {
                    if (validateImportResultCopy[j].status === 'invalid') {
                        validateImportResultCopy.splice(j, 1);
                    }
                }
            } else if (operation === 'createNewAll') {
                for (var k=validateImportResultCopy.length-1; k>=0; k--) {
                    if (validateImportResultCopy[k].status === 'invalid') {
                        validateImportResultCopy.splice(k, 1);
                    } else if (validateImportResultCopy[k].status === 'valid_exists') {
                        validateImportResultCopy[k].wiki_name = validateImportResultCopy[k].wiki_name + '(' + validateImportResultCopy[k].numbering + ')';
                        validateImportResultCopy[k].path = validateImportResultCopy[k].path + '(' + validateImportResultCopy[k].numbering + ')';
                    }
                }
            } else {
                // as skipAll
                for (var m=validateImportResultCopy.length-1; m>=0; m--) {
                    if (validateImportResultCopy[m].status !== 'valid' && validateImportResultCopy[i].status !== 'valid_duplicated') {
                        validateImportResultCopy.splice(m, 1);
                    }
                }
            }
            return validateImportResultCopy;
        }

        function showAlertInfo(validateImportResult, $alertInfoForm) {
            $('#alertInfo').modal('show');
            $('#importWiki').modal('hide');
            showAlertInfoBtn();
            if (validateImportResult.duplicated_folder.length > 0) {
                // show duplicated folder sentence
                $('#attentionDuplicatedFolder').css('display', '');
                // show Close Btn
                $('#closeAlertInfo').css('display', '');
                // hide the display of operations for all
                $alertInfoForm.find('.partOperationAll').css('display', 'none');
                // show duplicated import folder list
                validateImportResult.duplicated_folder.forEach(function(item) {
                    $('#duplicatedFolder ul').append('<li>' + item + '</li>');
                });
            } else {
                validateImportResultData = validateImportResult.data;
                // show the Btn of operations for all
                $('.btnAll').css('display', '');
                // show duplicated wiki page infomation
                validateImportResultData.forEach(function(item) {
                    if (item.status === 'valid_exists') {
                        $alertInfoForm.find('.partOperationAll').css('display', '');
                        $('#validateInfo ul').append('<li>' + (item.path).slice(1) + '</li>')
                        $('#perFileDifinitionForm ul').append('<li id="' + (item.path).slice(1) + '" style="display: flex;justify-content: flex-end;">' + '<div style="display: list-item; position: absolute; left: 55px; max-width: 410px;">' +  (item.path).slice(1) + '</div>' + selectOperation + '</li>');
                    } else if (item.status === 'valid_duplicated'){
                        $('#attentionDuplicatedInfo').css('display', '');
                        $('#duplicatedInfo ul').append('<li>' + (item.path).slice(1) + '</li>')
                    }
                });
            }
        }

        async function requestValidateImportTask(url, $alertInfoForm, $submitForm) {
            await new Promise(function(resolve){
                result = validateImportTaskPromise(url, $alertInfoForm, $submitForm)
                resolve();
            });
            return result
        }

        async function validateImportTaskPromise(url, $alertInfoForm, $submitForm) {
            return $.ajax({
                type: 'GET',
                cache: false,
                url: url,
                dataType: 'json'
            }).fail(function (response) {
                if (response.status !== 0) {
                    $importErrorMsg.text(response.status + ' : Error occurred when wiki validate.');
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
                        $importErrorMsg.text(response.responseJSON.message_long);
                    } else {
                        $importErrorMsg.text('Error occurred when wiki import.');
                    }
                }
            });
        }

        function showErrModal($importResult, $alertInfoForm) {
            // show import error modal.
            importErrors.push(...wikiImportResult.import_errors)
            var importErrorMsg = createErrMsg(importErrors);
            $('#importWiki').modal('hide');
            $('#alertInfo').modal('hide');
            $('#importResult').modal('show');
            $('#showImportError').append('<p>' + importErrorMsg + '</p>')
            $importResult.find('#showImportError').css('display', '');
            $alertInfoForm.find('.btnAll').css('display', 'none');
        }

        function createErrMsg(errorList) {
            var errMsg = 'The following wiki pages could not be imported.';
            for (var i = 0; i < errorList.length; i++) {
                errMsg += '<br>' + errorList[i];
            }
            return errMsg;
        }

        async function intervalGetCeleryTaskResult(url, ms, timeout, operation) {
            var count = 0;
            var result = '';
            var timeoutCtn = timeout * 1000 / ms
            while (count < timeoutCtn) {
                await new Promise(function(resolve){
                    setTimeout(async function(){
                        result = await getCeleryTaskResult(url, operation)
                        resolve();
                    }, ms);
                });
                if (result) {
                    if(result.aborted) {
                        alert('Wiki import aborted.')
                        dispBtnWhenAbort();
                        $('#importWiki').modal('hide');
                        $('#alertInfo').modal('hide');
                    }
                    break;
                }
                count++;
            }
            if (count === timeoutCtn){
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
                        $importErrorMsg.text(response.responseJSON.message_long);
                    } else {
                        alert('import error');
                    }
                    return;
                }
            });
        }

        function cleanCeleryTask() {
            var cleanTasksUrl = ${ urls['api']['base'] | sjson, n } + 'clean_celery_tasks/';
            $.ajax({
                type: 'POST',
                cache: false,
                url: cleanTasksUrl,
                dataType: 'json',
            }).done(function (response) {
                //dUrl = (location.href).replace(location.search, '')
                //window.location.assign(reloadUrl);
            });
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
        $alertInfoForm.find('.stopImport').on('click', function () {
            cleanCeleryTask();
            $alertInfoForm.find('.stopImport').css('display', 'none');
            $alertInfoForm.find('#continueImportWikiSubmit').attr('disabled', 'disabled').text('${_("Aborting...")}');
        });
        $importWikiForm.find('.stopImport').on('click', function () {
            $importWikiForm.find('.stopImport').css('display', 'none');
            $importWikiForm.find('#importWikiSubmit').attr('disabled', 'disabled').text('${_("Aborting...")}');
            cleanCeleryTask();
        });
        $('#importWiki').on('show.bs.modal', function () {
            showImportBtn();
        });

        function showImportBtn() {
            $importWikiForm.find('#importWikiSubmit').attr('disabled', false).css('display', '').text('${_("Import")}');
            $importWikiForm.find('#closeImport').css('display', 'none');
            $importErrorMsg.text('');
        }
        function showPerFileDefinition() {
            $alertInfoForm.find('.partOperationAll').css('display', 'none');
            $alertInfoForm.find('.btnAll').css('display', 'none');
            $alertInfoForm.find('.btnIndividual').css('display', '');
            $alertInfoForm.find('#perFileDifinitionForm').css('display', '');
        }
        function showAlertInfoBtn() {
            $alertInfoForm.find('#continueImportWikiSubmit').attr('disabled', false).css('display', '').text('${_("Import")}');;
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
            $importWikiForm.find('#closeImport').css('display', '');
            $importWikiForm.find('.stopImport').css('display', 'none');
            $alertInfoForm.find('.stopImport').css('display', 'none');
            $alertInfoForm.find('#continueImportWikiSubmit').css('display', 'none');
            $importWikiForm.find('#importWikiSubmit').css('display', 'none');
            $alertInfoForm.find('#perFileDefinition').css('display', 'none');
            $alertInfoForm.find('#backalertInfo').css('display', 'none');
        }
        function dispBtnWhenAbort() {
            $alertInfoForm.find('#continueImportWikiSubmit').attr('disabled', false).text('${_("Import")}');
            $importWikiForm.find('#importWikiSubmit').attr('disabled', false).text('${_("Import")}');
            $importWikiForm.find('.stopImport').css('display', 'none');
            $alertInfoForm.find('.stopImport').css('display', 'none');
            $alertInfoForm.find('.btnAll').attr('disabled', false).css('display', '');
            $alertInfoForm.find('.btnIndividual').attr('disabled', false).css('display', '');
        }
    });
</script>
