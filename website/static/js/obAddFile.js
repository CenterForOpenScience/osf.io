;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeahead', 'typeaheadSearch', 'dropzone'], function() {
            global.ObAddFile = factory(jQuery);
            $script.done('obAddFile');
        });
    } else {
        global.ObAddFile = factory(jQuery);
    }
}(this, function ($) {
    'use strict';

    var namespace = 'AddFile';
    var $obDropzone = $('#obDropzone');
    var $obDropzoneSelected = $('#obDropzoneSelected');
    var $uploadProgress = $('#uploadProgress');
    var $addLink = $('#addLink'+ namespace);
    var $fakeAddLink = $('#fakeAddLinkAddFile'); // perm disabled button until file uploaded, button is enabled by project 
    var $obDropzoneError = $('#obDropzoneError');
    var $uploadIcon = $('#uploadIcon');
    var $obDropzoneFilename = $('#obDropzoneFilename');
    var $inputProjectAddFile = $('#inputProjectAddFile');

    var uploadCounter = 1; // used to track upload count while uploading

    var myDropzone = new Dropzone('div#obDropzone', { 
        url: '/', // specified per upload
        autoProcessQueue: false, 
        createImageThumbnails: false,
        //over
        maxFiles:9000,
        uploadMultiple: false,
        maxFilesize: 1,

        uploadprogress: function(file, progress) { // progress bar update
            $('#uploadProgress').attr('value', Math.round(progress));
      },

        init: function() {
            var submitButton = document.querySelector('#addLink' + namespace);
            myDropzone = this;

            // Submit logic
            submitButton.addEventListener('click', function() {
                var projectRoute = get_route($addLink);
                
                $addLink.attr('disabled', true);
                $uploadProgress.show();

                myDropzone.options.url = projectRoute + 'osffiles/';
                myDropzone.processQueue(); // Tell Dropzone to process all queued files.
            });

            var clearError = document.querySelector('#obDropzone');            
            clearError.addEventListener('click', function() {
               $obDropzoneError.empty(); // remove any lingering errors on click

            });


            // clear dropzone logic
            var clearButton = document.querySelector('#clearDropzone');            
            clearButton.addEventListener('click', function() {

                $obDropzone.show(); // swap filedisplay with file dropzone
                $obDropzoneSelected.hide();
                
                $addLink.hide(); // swap active link with pseudo button
                $fakeAddLink.show();

                myDropzone.removeAllFiles();
                $('#obDropzoneError').empty();

            });

            // file add error logic
            this.on('error', function(file){
                var file_name = file.name;
                var file_size = file.size;
                myDropzone.removeFile(file);
                if(myDropzone.files.length===0){
                    $obDropzone.show(); // swap filedisplay with file dropzone
                    $obDropzoneSelected.hide();
                    
                    $addLink.hide(); // swap active link with pseudo button
                    $fakeAddLink.show();

                    myDropzone.removeAllFiles();
                }

                if(file_size > myDropzone.options.maxFilesize){

                    $obDropzoneError.append('<div>' + file_name + ' is too big (max = ' + myDropzone.options.maxFilesize + ' MiB) and was not added to the upload queue.</div>');
                    $obDropzoneError.show();
                }else{
                    $obDropzoneError.text(file_name + 'could not be added to the upload queue'); // I don't know if this will ever be called, just a back up error handling
                    $obDropzoneError.show();
                }
            });

            this.on('drop',function(){ // clear errors on drop or click 
                $('#obDropzoneError').empty();
            });

            // upload and process queue logic
            this.on('success',function(){
                $obDropzoneFilename.text(uploadCounter + ' / ' + myDropzone.files.length + ' files');
                 myDropzone.processQueue(); // this is a bit hackish -- it fails to process full queue but this ensures it runs the process again after each success.
                 uploadCounter+= 1;
                 if(uploadCounter> myDropzone.files.length){ // when finished redirect to project/component page where uploaded. 
                    
                    //redirect to project or componenet
                    if(typeof $addLink.prop('linkIDComponent')!=='undefined'){
                        redirect_to_poc('Component');
                    }else{
                        redirect_to_poc('Project');
                    }
                }
            });

            // add file logic and dropzone to file display swap
            this.on('addedfile', function() {
                if(myDropzone.files.length>1){
                    $uploadIcon.attr('src', '/static/img/upload_icons/multiple_blank.png');
                    $obDropzoneFilename.text(myDropzone.files.length + ' files');
                }else{
                    // $('#obDropzone').click();
                    var file_name = truncateFilename(myDropzone.files[0].name);
                    $uploadIcon.attr('src', '/static/img/upload_icons/' + get_dz_icon(file_name));
                    $obDropzoneFilename.text(file_name);
                }

                $obDropzone.hide(); // swap dropzone with file display
                $obDropzoneSelected.show();

                $fakeAddLink.hide(); // swap fake with real
                $addLink.show();
                
                $inputProjectAddFile.focus();
                $inputProjectAddFile.css('background-color', 'white !important;');
            });
        }
});

    var icon_list = [
    '_blank',
    '_page',
    'aac',
    'ai',
    'aiff',
    'avi',
    'bmp',
    'c',
    'cpp',
    'css',
    'dat',
    'dmg',
    'doc',
    'dotx',
    'dwg',
    'dxf',
    'eps',
    'exe',
    'flv',
    'gif',
    'h',
    'hpp',
    'html',
    'ics',
    'iso',
    'java',
    'jpg',
    'js',
    'key',
    'less',
    'mid',
    'mp3',
    'mp4',
    'mpg',
    'odf',
    'ods',
    'odt',
    'otp',
    'ots',
    'ott',
    'pdf',
    'php',
    'png',
    'ppt',
    'psd',
    'py',
    'qt',
    'rar',
    'rb',
    'rtf',
    'sass',
    'scss',
    'sql',
    'tga',
    'tgz',
    'tiff',
    'txt',
    'wav',
    'xls',
    'xlsx',
    'xml',
    'yml',
    'zip'
    ];


// Helper Functions
    // redictor to project or component
    function redirect_to_poc(poc){ // str project or componenet (poc)
        var url = '/'+ $addLink.prop('linkID' + poc); 
            if(url !== '/undefined'){
            window.location = url;
        }
    }

    // ensure it is not 
    function get_route(addLink){
        if(typeof addLink.prop('routeIDComponent')!=='undefined'){
            return addLink.prop('routeIDComponent');
        }else{
            return addLink.prop('routeIDProject');
        }
    }

    // this takes a filename and finds the icon for it
    function get_dz_icon(file_name){    
        var ext = file_name.split('.').pop().toLowerCase();
        if(icon_list.indexOf(ext) >= 0){
            return ext + '.png';
        }else{
            return '_blank.png';
        }
    }

    // if has an extention return it, else return the last three in a string
    function getStringEnd(string){
        if(string.indexOf('.') !== -1){
            return string.split('.').pop().toLowerCase();
        }else{
            return string.substring(string.length-3);    
        }
    }

    // truncate long file names
    function truncateFilename(string){
        var ext = getStringEnd(string);
        if (string.length > 40){
            return string.substring(0, 40-ext.length-3) + '...' + ext;
        }else{
            return string;
        }
    }

    function ObAddFile(){
        var typeaheadsearch1  = new TypeaheadSearch(namespace, 'Project', 1);
        var typeaheadsearch2  = new TypeaheadSearch(namespace, 'Component',0);
    }

    return ObAddFile;
}));
