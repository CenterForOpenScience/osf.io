<!-- OSF Upload -->
<script type="text/html" id="osf-upload">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="osf-upload-open">
  <div id="selectedFile">File(s) selected for upload:
    <br>
    <br>
        <div data-bind="foreach: selectedFiles">
            <span data-bind="text: data.name"></span>
            <button data-bind="click: $parent.unselectFile"
                    style="margin-left: 5px;"
                    class="btn btn-xs btn-danger fa fa-times"></button>
        </div>
  </div>
  <div data-bind="attr: {id: $data.uid}, osfUploader"><!-- TODO: osfUploader attribute may not connect to anything? -->
    <div class="spinner-loading-wrapper">
      <div class="ball-scale ball-scale-blue">
          <div></div>
      </div>
      <p class="m-t-sm fg-load-message"> Loading files...  </p>
    </div>
  </div>
</script>

<script type="text/html" id="osf-upload-toggle">
  <span data-bind="text: UPLOAD_LANGUAGE"></span>
  <br>
  <br>
    <div id="selectedFile">File(s) selected for upload:
        <div data-bind="foreach: selectedFiles">
            <span data-bind="text: data.name"></span>
            <button data-bind="click: $parent.unselectFile"
                    style="margin-left: 5px;"
                    class="btn btn-xs btn-danger fa fa-times"></button>
            <br />
            <div data-bind="visible: $parent.descriptionVisible">
                <p>Description: (optional)</p>
                <input data-bind="valueUpdate: 'keyup', value: data.descriptionValue" type="text" class="form-control">
            </div>
        </div>
  </div>
  <a data-bind="click: toggleUploader">Attach File</a>
  <span data-bind="visible: showUploader">
    <div data-bind="attr: {id: $data.uid}, osfUploader">
      <div class="container">
	      <p class="m-t-sm fg-load-message">
          <span class="ball-pulse ball-scale-blue">
              <div></div>
              <div></div>
              <div></div>
          </span>  Loading files...
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
