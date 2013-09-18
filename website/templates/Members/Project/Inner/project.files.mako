<%inherit file="project.view.mako" />
<% import website.settings %>
<%
    is_contributor = node_to_use.is_contributor(user)
    editable = is_contributor and not node_to_use.is_registration
    disabled_class = "" if editable else " disabled"
%>

<form id="fileupload" action="/api/v1${node_to_use.url() + '/files/upload'}" method="POST" enctype="multipart/form-data">
        <!-- The fileupload-buttonbar contains buttons to add/delete files and start/cancel the upload -->
        <div class="row fileupload-buttonbar">
            <div class="span7">
                <!-- The fileinput-button span is used to style the file input field as button -->
                <span class="btn btn-success fileinput-button${disabled_class}">
                    <i class="icon-plus icon-white"></i>
                    <span>Add files...</span>
                    <input type="file" name="files[]" multiple>
                </span>
                <button type="submit" class="btn btn-primary start${disabled_class}">
                    <i class="icon-upload icon-white"></i>
                    <span>Start upload</span>
                </button>
            </div>
            <!-- The global progress information -->
            <div class="span5 fileupload-progress fade">
                <!-- The global progress bar -->
                <div style='margin-bottom:0' class="progress progress-success progress-striped active" role="progressbar" aria-valuemin="0" aria-valuemax="100">
                    <div class="bar" style="width:0%;"></div>
                </div>
                <!-- The extended global progress information -->
                <div class="progress-extended">&nbsp;</div>
            </div>
        </div>
        <!-- The loading indicator is shown during file processing -->
        <div class="fileupload-loading"></div>
        <br>
        <!-- The table listing the files available for upload/download -->
        <div id='fileWidgetLoadingIndicator' class="progress progress-striped active">
            <div class="bar" style="width: 100%;">Loading...</div>
        </div>
        <table id='filesTable' role="presentation" class="table table-striped" style='display:none'>
            <thead>
                <tr>
                    <th>Filename</th>
                    <th>Date Modified</th>
                    <th>File Size</th>
                    <th colspan=2>Downloads</th>
                </tr>
            </thead>
            <tbody class="files">
            </tbody>
        </table>
</form>
<!-- The template to display files available for upload -->
<script id="template-upload" type="text/x-tmpl">
{% for (var i=0, file; file=o.files[i]; i++) { %}
    <tr class="template-upload fade">
        <td class="preview"><span class="fade"></span></td>
        <td class="name"><span>{%=file.name%}</span></td>
        <td class="size"><span>{%=o.formatFileSize(file.size)%}</span></td>
        {% if (file.error) { %}
            <td class="error" colspan="2"><span class="label label-important">{%=locale.fileupload.error%}</span> {%=locale.fileupload.errors[file.error] || file.error%}</td>
        {% } else if (o.files.valid && !i) { %}
            <td colspan="2">
                <div class="progress progress-success progress-striped active" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="bar" style="width:0%;"></div></div>
            </td>
            <td class="start">{% if (!o.options.autoUpload) { %}
                <button class="btn btn-primary">
                    <i class="icon-upload icon-white"></i>
                    <span>{%=locale.fileupload.start%}</span>
                </button>
            {% } %}</td>
        {% } else { %}
            <td colspan="2"></td>
        {% } %}
    </tr>
{% } %}
</script>
<!-- The template to display files available for download -->
<script id="template-download" type="text/x-tmpl">
{% for (var i=0, file; file=o.files[i]; i++) { %}
    <tr class="template-download fade">
        {% if (file.error) { %}
            <td class="name"><span>{%=file.name%}</span></td>
            <td></td>
            <td class="size"><span>{%=o.formatFileSize(file.size)%}</span></td>
            <td class="error" colspan="3"><span class="label label-important">{%=locale.fileupload.error%}</span> {%=locale.fileupload.errors[file.error] || file.error%}</td>
        {% } else { %}
            <td class="name">
                <a href="{%=file.url%}" title="{%=file.name%}">{%=file.name%}</a>
            </td>
            {% if (file.hasOwnProperty('action_taken') && file.action_taken === null) { %}
                    <td colspan=5>
                        <span class='label label-info'>No Action Taken</span> {%= file.message %}
                    </td>
            {% } else { %}
            <td>{%=file.date_uploaded%}</td>
            <td class="size"><span>{%=o.formatFileSize(file.size)%}</span></td>
            <td>{%=file.downloads%}</td>
            <td><a href="{%=file.download_url%}" download="{%=file.name%}"><i class="icon-download-alt"></i></a></td>
            <td><form style='margin:0' method='post' class='fileDeleteForm' action='${node_to_use.url() + '/files/delete/{%=file.name%}'}'>
                <button type="button" class="btn btn-danger btn-delete${disabled_class}"${ "onclick='deleteFile(this)'" if editable else ""}>
                    <i class="icon-trash icon-white"></i>
                    <span>Delete</span>
                </button>
                </form>
            </td>
            {% } %}
        {% } %}
        ##<td class="delete">
        ##    <button class="btn btn-danger" data-type="{%=file.delete_type%}" data-url="{%=file.delete_url%}">
        ##        <i class="icon-trash icon-white"></i>
        ##        <span>{%=locale.fileupload.destroy%}</span>
        ##    </button>
        ##    <input type="checkbox" name="delete" value="1">
        ##</td>
    </tr>
{% } %}
</script>
<script>
function deleteFile(button) {
   var url = $(button).parents('form.fileDeleteForm').attr('action');
    $.post(url, function(data) {
            if(!data.success) {
                alert('Error!');
            } else {
                $(button).parents('.template-download').fadeOut();
            }
    })
}

$(function () {
    'use strict';

    // Initialize the jQuery File Upload widget:
    $('#fileupload').fileupload();
    $('#fileupload').fileupload('option',{
        url: '/api/v1${node_to_use.url() + '/files/upload/'}',
        acceptFileTypes: /(\.|\/)(.*)$/i,
        maxFileSize: ${website.settings.max_upload_size}
    });

     // Load existing files:
     $('#fileupload').each(function () {
         var that = this;
         $.getJSON(this.action, function (result) {
             if (result && result.files.length) {
                 $(that).fileupload('option', 'done')
                     .call(that, null, {result: result.files});
             }
             $('#fileWidgetLoadingIndicator').fadeOut(400, function() {
                $('#filesTable').fadeIn(400)
             })

         });
     });
 });
</script>

<script src="/static/js/vendor/jquery.ui.widget.js"></script>
##%if website.settings.use_cdn_for_client_libs:
##<script src="http://blueimp.github.com/JavaScript-Templates/tmpl.min.js"></script>
##<script src="http://blueimp.github.com/JavaScript-Load-Image/load-image.min.js"></script>
##<script src="http://blueimp.github.com/JavaScript-Canvas-to-Blob/canvas-to-blob.min.js"></script>
##<script src="http://blueimp.github.com/cdn/js/bootstrap.min.js"></script>
##<script src="http://blueimp.github.com/Bootstrap-Image-Gallery/js/bootstrap-image-gallery.min.js"></script>
##%else:
    <script src="/static/tmpl.min.js"></script>
    <script src="/static/load-image.min.js"></script>
    <script src="/static/canvas-to-blob.min.js"></script>
    <script src="/static/bootstrap.min.js"></script>
    <script src="/static/bootstrap-image-gallery.min.js"></script>
##%endif
<script src="/static/js/jquery.iframe-transport.js"></script>
<script src="/static/js/jquery.fileupload.js"></script>
<script src="/static/js/jquery.fileupload-fp.js"></script>
<script src="/static/js/jquery.fileupload-ui.js"></script>
<script src="/static/js/locale.js"></script>
<script src="/static/js/main.js"></script>

<!-- The XDomainRequest Transport is included for cross-domain file deletion for IE8+ -->
<!--[if gte IE 8]><script src="/js/cors/jquery.xdr-transport.js"></script><![endif]-->

% if not editable:
    <script type="text/javascript">
        $('.fileupload-buttonbar .btn').on('click', function(event) {
            event.preventDefault();
        });
        $('input[name="files[]"]').css('cursor', 'default');
    </script>
% endif