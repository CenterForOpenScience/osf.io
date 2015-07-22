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
  <a data-bind="click: toggleUploader">Attach File</a>
  <span data-bind="visible: showUploader">
    <span data-bind="template: {data: $data, name: 'osf-upload-open'}"></span>
  </span>
</script>
