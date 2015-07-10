<!-- OSF Upload -->
<script type="text/html" id="osf-upload">
  <a data-bind="click: toggleUploader">Upload File</a>

    <div id="selectedFile">File selected for upload:  
	  <span id="fileName">no file selected</span>
	</div>
    <div data-bind="attr.id: $data.id, osfUploader"></div>

</script>
