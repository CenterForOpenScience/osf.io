<!-- OSF Upload -->
<script type="text/html" id="osf-upload">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="osf-upload-open">
  <div id="selectedFile">File selected for upload:
    <span data-bind="text: extra().selectedFileName">no file selected</span>
    <button data-bind="visible: hasSelectedFile,
                       click: unselectFile"
            style="margin-left: 5px;"
            class="btn btn-xs btn-danger fa fa-times"></button>
  </div>
  <div data-bind="attr.id: $data.uid, osfUploader">
    <div class="spinner-loading-wrapper">
      <div class="logo-spin logo-lg"></div>
      <p class="m-t-sm fg-load-message"> Loading files...  </p>
    </div>
  </div>
</script>

<script type="text/html" id="osf-upload-toggle">
  <div id="selectedFile">File selected for upload:
    <span id="fileName" data-bind="text: extra().selectedFileName">no file selected</span>
    <button data-bind="visible: hasSelectedFile,
                       click: unselectFile"
            style="margin-left: 5px;"
            class="btn btn-xs btn-danger fa fa-times"></button>
  </div>
  <a data-bind="click: toggleUploader">Attach File</a>
  <span data-bind="visible: showUploader">
    <div data-bind="attr.id: $data.uid, osfUploader">
      <div class="container">
	<p class="m-t-sm fg-load-message">
          <span class="logo-spin logo-sm"></span>  Loading files...
        </p>
      </div>
    </div>
  </span>
</script>

<!--Author Import -->
<script type="text/html" id="osf-author-import">
    <h3 data-bind="text: value"></h3>
    <a href="#addContributors" data-toggle="modal" class="btn btn-success btn-md pull-right" >Add &plus;</a>
</script>



<!-- Add User Modal-->
<%include file="/project/modal_add_contributor.mako"/>
