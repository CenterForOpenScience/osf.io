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
    var $clearInputProjectAddFile = $('#clearInputProjectAddFile');
    var $clearInputComponentAddFile = $('#clearInputComponentAddFile');
    var $uploadIcon = $('#uploadIcon');
    var $obDropzoneFilename = $('#obDropzoneFilename');
    var $inputProjectAddFile = $('#inputProjectAddFile');

    var myDropzone = new Dropzone('div#obDropzone', { 
        url: '/', // specified per upload
        autoProcessQueue: false, 
        createImageThumbnails: false,
        maxFiles:1,
        uploadMultiple: false,

        uploadprogress: function(file, progress) { // progress bar update
            $('#uploadProgress').attr('value', Math.round(progress));
      },

        init: function() {
            var submitButton = document.querySelector('#addLink' + namespace);
            myDropzone = this;

            this.on('maxfilesexceeded', function(file){
                this.removeFile(file);
                $obDropzone.text(file_name);
                $obDropzone.css('background-image', icon_url);
            });

            submitButton.addEventListener('click', function() {
                var projectRoute = $addLink.prop('routeID');
                
                $addLink.attr('disabled', true);
                $uploadProgress.show();
                myDropzone.options.url = projectRoute + 'osffiles/';
                myDropzone.processQueue(); // Tell Dropzone to process all queued files.
            });

            var clearButton = document.querySelector('#clearDropzone');
            clearButton.addEventListener('click', function() {
                $clearInputProjectAddFile.click();
                $clearInputComponentAddFile.click();
                $obDropzoneSelected.hide();
                $obDropzone.show();
                delete $addLink.linkID;
                myDropzone.removeAllFiles();
            });


            // This reloads the window to the project you uploaded the file to...
            this.on('complete', function () {
                var url = '/'+ $addLink.prop('linkID'); 
                if(url !== '/undefined'){
                    window.location = url;
                }
            });


            // You might want to show the submit button only when 
            // files are dropped here:

            this.on('addedfile', function() {
                var file_name = truncateFilename(myDropzone.files[0].name);
                // var icon_url = 'url(/static/img/upload_icons/' + get_dz_icon(file_name) + ')';
                var icon_url = '/static/img/upload_icons/' + get_dz_icon(file_name);
                
                $uploadIcon.attr('src', icon_url);
                $obDropzoneFilename.text(file_name);


                // $('#obDropzoneReveal').fadeIn();
                $obDropzone.hide();
                $obDropzoneSelected.show();
                
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
        if (string.length > 50){
            return string.substring(0, 50-ext.length-3) + '...' + ext;
        }else{
            return string;
        }
    }

    function ObAddFile(){
        var typeaheadsearch1  = new TypeaheadSearch(namespace, "Project", 1);
        var typeaheadsearch2  = new TypeaheadSearch(namespace, 'Component');

    }

    return ObAddFile;
}));


