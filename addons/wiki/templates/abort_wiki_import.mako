<!-- Abort Wiki Import Modal -->
<div class="modal fade" id="abortWikiImport">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h3 class="modal-title">${_("Abort wiki import")}</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                <div id="alert" style="padding-bottom:10px">${_("Any wiki imports in process will be aborted. This action is irreversible.")}</div>
                <p class="text-danger abortErrorMsg"> </p>
            </div><!-- end modal-body -->
            <div class="modal-footer">
                <a id="close" href="#" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</a>
                <a id="abort-wiki-import" class="btn btn-danger">${_("Abort")}</a>
            </div><!-- end modal-footer -->
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script type="text/javascript">
    $(document).ready(function() {
        var $submitForm = $('#abort-wiki-import');
        var $abortErrorMsg = $('.abortErrorMsg');
        $('#abort-wiki-import').on('click', async function () {
            $submitForm.attr('disabled', 'disabled').text('${_("Aborting")}');
            const cleanTasksUrl = ${ urls['api']['base'] | sjson, n } + 'clean_celery_tasks/';
            const getAbortWikiImportResultUrl = ${ urls['api']['base'] | sjson, n } + 'get_abort_wiki_import_result/';
            const abortWikiImport = await requestAbortWikiImport(cleanTasksUrl, $abortErrorMsg);
            const abortTaskResult = await intervalGetAbortWikiImportResult(getAbortWikiImportResultUrl, 1000, 60, 'abort wiki import')
        });
    });

    async function requestAbortWikiImport(url, $abortErrorMsg) {
        await new Promise(function(resolve){
            result = abortWikiImportPromise(url, $abortErrorMsg)
            resolve();
        });
        return result
    }

    async function abortWikiImportPromise(cleanTasksUrl, $abortErrorMsg) {
        return $.ajax({
            type: 'POST',
            cache: false,
            url: cleanTasksUrl,
            dataType: 'json',
        }).fail(function (response) {
            if (response.status !== 0) {
                $abortErrorMsg.text('Error occurred when abort wiki import.');
            }
        });
    }

    async function intervalGetAbortWikiImportResult(url, ms, timeout, operation) {
        var count = 0;
        var result = '';
        var timeoutCtn = timeout * 1000 / ms
        while (count < timeoutCtn) {
            await new Promise(function(resolve){
                setTimeout(async function(){
                    result = await getAbortWikiImportResult(url, operation)
                    resolve();
                }, ms);
            });
            if (result) {
                if(result.aborted) {
                    alert('Wiki import aborted.')
                    var reloadUrl = (location.href).replace(location.search, '')
                    window.location.assign(reloadUrl);
                }
                break;
            }
            count++;
        }
        if (count === timeoutCtn){
            console.log('timeout the operation');
            return;
        }
        return result;
    }

    async function getAbortWikiImportResult(getAbortWikiImportUrl, operation) {
        console.log('get celery task result start')
        return $.ajax({
            type: 'GET',
            cache: false,
            url: getAbortWikiImportUrl,
            dataType: 'json',
        }).fail(function (response) {
            if (response.status !== 0) {
                alert('abort error');
                return;
            }
        });
    }
</script>
