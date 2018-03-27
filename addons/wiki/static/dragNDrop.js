var $ = require('jquery');
var $osf = require('js/osfHelpers');
var ctx = window.contextVars;
var Range = ace.require('ace/range').Range;

var getExtension = function(filename) {
    return /(?:\.([^.]+))?$/.exec(filename)[1];
};
var validImgExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp'];
var imageFolder = 'Wiki images';

var autoIncrementFileName = function(name, nameList) {
    var num = 1;
    var newName;
    var ext = getExtension(name);
    var baseName = name.replace('.' + ext, '');

    rename:
    while (true) {
        for (var i = 0; i < nameList.length; i++) {
            newName = baseName + '(' + num + ').' + ext;
            if (nameList[i] === newName) {
                num += 1;
                newName = baseName + '(' + num + ').' + ext;
                continue rename;
            }
        }
        break;
    }
    return newName;
};


var localFileHandler = function(files, cm, init, fixupInputArea) {
    var multiple = files.length > 1;
    var urls = [];
    var name;
    var fileNames = [];
    var ext;
    var num = cm.addLinkDef(init) + 1;
    var promises = [];
    var editor = ace.edit('editor');
    editor.disable();
    getOrCreateWikiImagesFolder().fail(function(response) {
        notUploaded(response, multiple);
        editor.enable();
    }).done(function(path) {
        $.ajax({ // Check to makes sure we don't overwrite a file with the same name.
            url: ctx.waterbutlerURL + 'v1/resources/' + ctx.node.id + '/providers/osfstorage' + encodeURI(path) + '?meta=',
            beforeSend: $osf.setXHRAuthorization,
        }).done(function (response) {
            fileNames = response.data.map(function(file) {
                return file.attributes.name;
            });
            if (path) {
                var newName;
                $.each(files, function (i, file) {
                    if (fileNames.indexOf(file.name) !== -1) {
                        newName = autoIncrementFileName(file.name, fileNames);
                    }
                    ext = getExtension(file.name);
                    name = newName ? newName : file.name;
                    if (validImgExtensions.indexOf(ext.toLowerCase()) <= -1) {
                        $osf.growl('Error', 'This file type cannot be embedded  (' + file.name + ')', 'danger');
                    } else {
                        var waterbutlerURL = ctx.waterbutlerURL + 'v1/resources/' + ctx.node.id + '/providers/osfstorage' + encodeURI(path) + '?name=' + encodeURI(name) + '&type=file';
                        $osf.trackClick('wiki', 'dropped-image', ctx.node.id);
                        promises.push(
                            $.ajax({
                                url: waterbutlerURL,
                                type: 'PUT',
                                processData: false,
                                contentType: false,
                                beforeSend: $osf.setXHRAuthorization,
                                data: file,
                            }).done(function (response) {
                                urls.splice(i, 0, response.data.links.download + '?mode=render');
                            }).fail(function (response) {
                                notUploaded(response, false, cm, init, fixupInputArea, path, file);
                            })
                        );
                    }
                });
                $.when.apply(null, promises).done(function () {
                    $.each(urls, function (i, url) {
                        cm.doLinkOrImage(init, null, true, url, multiple, num + i);
                    });
                    fixupInputArea();
                    editor.enable();
                });
            } else {
                notUploaded(null, multiple);
            }
        }).fail(function (response) {
            notUploaded(response, false, cm, init, fixupInputArea, path);
        });
    });
};

var remoteFileHandler = function(html, url, cm, init, fixupInputArea) {
    var getSrc = /src="([^"]+)"/;
    var src = getSrc.exec(html);
    // The best way to get the image is from the src attribute of image html if available
    // If not we will move forward with the URL that is provided to use
    var imgURL = src ? src[1] : url;

    // We currently do not support data:image URL's
    if (imgURL.substring(0, 10) === 'data:image') {
        $osf.growl('Error', 'Unable to handle this type of link.  Please either find another link or save the image to your computer and import it from there.');
        fixupInputArea(init);
        return;
    }
    // If we got the image url from src we can treat it as an image
    var isImg = src;
    if (!isImg) {
        // Check our url to see if it ends in a valid image extension.
        // If yes, we can treat it as an image.  Otherwise, it gets treated as a normal link
        var ext = getExtension(imgURL);
        isImg = !!ext ? validImgExtensions.indexOf(ext.toLowerCase()) > -1 : false;
    }
    cm.doLinkOrImage(init, fixupInputArea, isImg, imgURL);
};

/**
 * Adds Image/Link Drag and Drop functionality to the Ace Editor
 *
 * @param editor - Ace Editor instance
 * @param panels - PanelCollection used for getting TextAreaState
 * @param cm - CommandManager
 */
var addDragNDrop = function(editor, panels, cm, TextareaState) {
    var element = editor.container;
    editor.getPosition = function(x, y) {
        var config = editor.renderer.$markerFront.config;
        var height = config.lineHeight;
        var width = config.characterWidth;
        var row = Math.floor(y/height) < editor.session.getScreenLength() ? Math.floor(y/height) : editor.session.getScreenLength() - 1;
        var column = Math.floor(x/width) < editor.session.getScreenLastRowColumn(row) ? Math.floor(x/width) : editor.session.getScreenLastRowColumn(row);
        return {row: row, column: column};
    };
    editor.enable = function() {
        $('#aceLoadingBall').css('display', 'none');
        editor.container.style.pointerEvents = 'initial';
        editor.container.style.opacity = 1;
        editor.renderer.setStyle('disabled', false);
    };
    editor.enable();

    editor.disable = function() {
        $('#aceLoadingBall').css('display', 'inherit');
        editor.container.style.pointerEvents = 'none';
        editor.container.style.opacity = 0.1;
        editor.renderer.setStyle('disabled', true);
    };

    editor.marker = {};
    editor.marker.cursor = {};
    editor.marker.active = false;
    editor.marker.update = function(html, markerLayer, session, config) {
        var height = config.lineHeight;

        var width = config.characterWidth;
        var top = markerLayer.$getTop(this.cursor.row, config);
        var left = markerLayer.$padding + this.cursor.column * width;
        html.push(
            '<div class=\'drag-drop-cursor\' style=\'',
            'height:', height, 'px;',
            'top:', top, 'px;',
            'left:', left, 'px; width:', width, 'px\'></div>'
        );
    };

    editor.marker.redraw = function() {
        this.session._signal('changeFrontMarker');
    };

    /**
     * This is called when an item is dragged over the editor
     *
     * Enables the 'drop' stuff to happen later
     *
     * Also adds a second cursor that follows around the mouse cursor and signifies where the image/link will
     * be inserted
     */
    element.addEventListener('dragover', function(event) {
        event.preventDefault();
        event.stopPropagation();
        if (!editor.marker.active) {
            editor.marker.active = true;
            editor.marker.session = editor.session;
            editor.marker.session.addDynamicMarker(editor.marker, true);
        }
        editor.marker.cursor = editor.getPosition(event.offsetX, event.offsetY);
        editor.marker.redraw();
        var effect;
        try {
          effect = event.dataTransfer.effectAllowed;
        } catch (_error) {}
        event.dataTransfer.dropEffect = 'move' === effect || 'linkMove' === effect ? 'move' : 'copy';
    }, false);

    /**
     * Called when a 'drop' occurs over the editor
     *
     * Takes a snapshot of what the current text is in order to be able to edit it as necessary
     *
     * Handles the errors that may occur with bad links/files
     */
    element.addEventListener('drop', function(event) {
        event.preventDefault();
        event.stopPropagation();

        var state = new TextareaState(panels);
        var offset = state.selection.length;
        state.selection = '';
        if (!state) {
            return;
        }

        /**
         * sets init to be the current state of the editor
         *
         * init.before is everything before the drag and drop cursor
         *
         * init.after is everything after the drag and drop cursor
         */
        var init = state.getChunks();
        init.before = editor.session.getTextRange(new Range(0, 0, editor.marker.cursor.row, editor.marker.cursor.column));
        init.after = editor.session.getTextRange(new Range(editor.marker.cursor.row, editor.marker.cursor.column + offset, Number.MAX_VALUE, Number.MAX_VALUE));

        /**
         * Sets the values of the input area to be the current values of init.before, init.selection, and init.after
         *
         * init.before = everything before cursor/selection
         *
         * init.selection = text that is highlighted
         *
         * init.after = everything after cursor.selection
         */
        var fixupInputArea = function() {
            state.setChunks(init);
            state.restore();
        };

        /**
         * If the item being dragged is from elsewhere online, html and/or URL will be defined
         *
         * html will be the HTML block for the element being dragged
         *
         * url will be some sort of url that is hopefully an image url (or an image can be parsed out)
         *
         * remoteFileHandler() will attempt to figure this out and react accordingly
         */
        var html = event.dataTransfer.getData('text/html');
        var url = event.dataTransfer.getData('URL');
        if (!!html || !!url) {
            remoteFileHandler(html, url, cm, init, fixupInputArea);
        } else {
            /**
             * If event.dataTransfer does not have html or url for the item(s), then try to upload it as a file
             *
             * localFileHandler() will deal with all of the error checking/handling for this
             */
            var files = event.dataTransfer.files;
            localFileHandler(files, cm, init, fixupInputArea);
        }
        editor.marker.session.removeMarker(editor.marker.id);
        editor.marker.redraw();
        editor.marker.active = false;
    }, true);

    /**
     * Called if something is dragged over the editor and then dragged back out
     *
     * Removes the second cursor
     */
    element.addEventListener('dragleave', function(event) {
        event.preventDefault();
        event.stopPropagation();
        editor.marker.session.removeMarker(editor.marker.id);
        editor.marker.redraw();
        editor.marker.active = false;
    });
};


var notUploaded = function(response, multiple, cm, init, fixupInputArea, path, file) {
    var files = multiple ? 'Files' : 'File';
    var editor = ace.edit('editor');
    if (response.status === 403) {
        $osf.growl('Error', 'File not uploaded. You do not have permission to upload files to' +
            ' this project.', 'danger');
        editor.enable();
    } else {
        $osf.growl('Error', files + ' not uploaded. Please refresh the page and try ' +
            'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
            'if the problem persists.', 'danger');
        editor.enable();
    }
};

/**
 * If the 'Wiki images' folder does not exist for the current node, createFolder generates the request to create it
 */
var createFolder = function() {
    return $.ajax({
        url: ctx.waterbutlerURL + 'v1/resources/' + ctx.node.id + '/providers/osfstorage/?name=' + encodeURI(imageFolder) + '&kind=folder',
        type: 'PUT',
        beforeSend: $osf.setXHRAuthorization,
    });
};

/**
 * Checks to see whether there is already a 'Wiki images' folder for the current node
 *
 * If the folder doesn't exist, it attempts to create the folder
 *
 * @return {*} The folder's path attribute if it exists/was created
 */
var getOrCreateWikiImagesFolder = function() {
    var folderUrl = ctx.apiV2Prefix + 'nodes/' + ctx.node.id + '/files/osfstorage/?filter[kind]=folder&fields[file]=name,path&filter[name]=' + encodeURI(imageFolder);
    return $.ajax({
        url: folderUrl,
        type: 'GET',
        beforeSend: $osf.setXHRAuthorization,
        dataType: 'json'
    }).then(function(response) {
        if (response.data.length > 0) {
            for (var i = 0, folder; folder = response.data[i]; i++) {
                var name = folder.attributes.name;
                if (name === imageFolder) {
                    return folder.attributes.path;
                }
            }
        }
        if (response.data.length === 0) {
            return createFolder().then(function(response) {
                return response.data.attributes.path;
            });
        }
    });
};

module.exports = addDragNDrop;
