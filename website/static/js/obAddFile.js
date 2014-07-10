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
    var $fakeAddLink = $('#fakeAddLinkAddFile');
    var uploadCounter = 1;

    // var $clearInputProjectAddFile = $('#clearInputProjectAddFile');
    // var $clearInputComponentAddFile = $('#clearInputComponentAddFile');
    
    var $uploadIcon = $('#uploadIcon');
    var $obDropzoneFilename = $('#obDropzoneFilename');
    var $inputProjectAddFile = $('#inputProjectAddFile');

    var myDropzone = new Dropzone('div#obDropzone', { 
        url: '/', // specified per upload
        autoProcessQueue: false, 
        createImageThumbnails: false,
        //over
        maxFiles:9000,
        uploadMultiple: false,

        uploadprogress: function(file, progress) { // progress bar update
            $('#uploadProgress').attr('value', Math.round(progress));
      },

        init: function() {
            var submitButton = document.querySelector('#addLink' + namespace);
            myDropzone = this;

            // this.on('maxfilesexceeded', function(file){
            //     // this.removeFile(file);
            // });

            submitButton.addEventListener('click', function() {
                var projectRoute = get_route($addLink);
                
                $addLink.attr('disabled', true);
                $uploadProgress.show();
                myDropzone.options.url = projectRoute + 'osffiles/';
                myDropzone.processQueue(); // Tell Dropzone to process all queued files.
            });

            var clearButton = document.querySelector('#clearDropzone');
            clearButton.addEventListener('click', function() {
                $obDropzoneSelected.hide();
                $addLink.hide();
                $obDropzone.show();
                $fakeAddLink.show();
                myDropzone.removeAllFiles();
            });

            this.on('success',function(){
                $obDropzoneFilename.text(uploadCounter + ' / ' + myDropzone.files.length + ' files');
                 myDropzone.processQueue();
                 uploadCounter+= 1;
                 if(uploadCounter> myDropzone.files.length){
                    if(typeof $addLink.prop('linkIDComponent')!=='undefined'){
                        var url = '/'+ $addLink.prop('linkIDComponent'); 
                        if(url !== '/undefined'){
                        window.location = url;
                        }
                    }else{
                        var url = '/'+ $addLink.prop('linkIDProject'); 
                        if(url !== '/undefined'){
                            window.location = url;
                        }
                    }
                 }
            });
            // This reloads the window to the project you uploaded the file to...
            // this.on('complete', function () {
            //     if(typeof $addLink.prop('linkIDComponent')!=='undefined'){
            //         var url = '/'+ $addLink.prop('linkIDComponent'); 
            //         if(url !== '/undefined'){
            //             // window.location = url;
            //         }
            //     }else{
            //         var url = '/'+ $addLink.prop('linkIDProject'); 
            //         if(url !== '/undefined'){
            //             // window.location = url;
            //         }
            //     }
            // });

            // You might want to show the submit button only when 
            // files are dropped here:

            this.on('addedfile', function() {
                if(myDropzone.files.length>1){
                    var icon_url = '/static/img/upload_icons/multiple_blank.png';
                    $uploadIcon.attr('src', icon_url);
                    $obDropzoneFilename.text(myDropzone.files.length + ' files');
                }else{
                    var file_name = truncateFilename(myDropzone.files[0].name);
                    var icon_url = '/static/img/upload_icons/' + get_dz_icon(file_name);
                    $uploadIcon.attr('src', icon_url);
                    $obDropzoneFilename.text(file_name);
                }

                // var icon_url = 'url(/static/img/upload_icons/' + get_dz_icon(file_name) + ')';
                

                // $('#obDropzoneReveal').fadeIn();
                $obDropzone.hide();
                $obDropzoneSelected.show();

                $fakeAddLink.hide();
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
        if (string.length > 50){
            return string.substring(0, 50-ext.length-3) + '...' + ext;
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


