<!-- OSF Upload -->
<script type="text/html" id="osf-upload">
    <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="osf-upload-open">
  <div id="selectedFile">File selected for upload:
    <span id="fileName" data-bind="text: selectedFileName">no file selected</span>
  </div>
  <div data-bind="attr.id: $data.id, osfUploader"></div>
</script>

<script type="text/html" id="osf-upload-toggle">
  <div id="selectedFile">File selected for upload:
    <span id="fileName" data-bind="text: selectedFileName">no file selected</span>
  </div>
  <a data-bind="click: toggleUploader">Attach File</a>
  <span data-bind="visible: showUploader">
    <div data-bind="attr.id: $data.id, osfUploader"></div>
  </span>
</script>

<!--Author Import -->
<script type="text/html" id="osf-author-import">
    <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="osf-import-button">
  <a data-bind="click: $root.authorDialog, visible: contributors.length > 1">Import Contributors</a>
</script>
