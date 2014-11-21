//LOAD TESTS
QUnit.module( "Fangorn Load Tests" );

    QUnit.test('Fangorn is loaded', function(assert) {
            assert.ok(typeof filebrowser === 'object', 'Fangorn is loaded as an object');
        });

    QUnit.test('Fangorn has options', function(assert) {
            assert.ok(typeof filebrowser.options === 'object', 'Fangorn has default options');
        });

//API TESTS
QUnit.module( "Fangorn API Tests" );

    QUnit.test('_fangornresolveIcons() works', function(assert) {
        var folder = filebrowser.grid.createItem({'kind': 'folder', 'name': 'resolveIconFolder', 'permissions':{edit:true, view:true}}, 1);
        var item = filebrowser.grid.createItem({'kind': 'item', 'name': 'resolveIconItem', 'permissions':{edit:true, view:true}}, 1);

        //Testing for Public Open Folders
        folder.open = true;
        var publicOpenFolder = filebrowser.options.resolveIcon(folder);

        //Testing for Public Closed Folders
        folder.open = false;
        var publicClosedFolder = filebrowser.options.resolveIcon(folder);

        //Testing for Pointer Folders
        folder.data.isPointer = true;
        var pointerFolder = filebrowser.options.resolveIcon(folder);

        //Testing for Private Folders
        folder.data.permissions.view = false;
        var privateFolder = filebrowser.options.resolveIcon(folder);

        //Testing for Generic Items
        var publicItem = filebrowser.options.resolveIcon(item);

        //Testing for Specific Item Type
        item.data.name = "resolveIconItem.txt";
        var publicSpecificItem = filebrowser.options.resolveIcon(item);

        item.data.icon = "pnggg";
        var publicSpecificDataItem = filebrowser.options.resolveIcon(item);

        assert.deepEqual(publicOpenFolder, m('i.icon-folder-open-alt', ' '), 'when item is folder and open returns with open folder icon.');
        assert.deepEqual(publicClosedFolder, m('i.icon-folder-close-alt', ' '), 'when item is folder and closed returns with closed folder sign.');
        assert.deepEqual(pointerFolder, m('i.icon-hand-right', ' '), 'when item is folder and isPointer is true returns pointer folder.');
        assert.deepEqual(privateFolder, m('img', { src : "/static/img/hgrid/fatcowicons/folder_delete.png" }), 'when item is folder and edit permission is false returns private folder.');
        assert.deepEqual(publicItem, m('i.icon-file-alt'), 'when item is item and public returns with generic icon.');
        assert.deepEqual(publicSpecificItem, m('img', { src : '/static/img/hgrid/fatcowicons/file_extension_txt.png'}), 'when item is item and public returns with respective icon.');
        assert.deepEqual(publicSpecificDataItem, m('i.fa.' + item.data.icon, ' '), 'when item is item and public returns with specific icon.');
    });

    QUnit.test('_fangornResolveToggle() works', function(assert) {
        var item = filebrowser.grid.createItem({'kind': 'folder', 'name': 'resolveToggle', 'permissions':{edit:true, view:true}}, 1);

        //Testing for Folders
        item.open = false;
        var resultFalse = filebrowser.options.resolveToggle(item);

        item.open = true;
        var resultTrue = filebrowser.options.resolveToggle(item);

        //Testing for Items
        item.kind = 'item';
        item.open = false;
        var resultItemFalse = filebrowser.options.resolveToggle(item);

        item.open = true;
        var resultItemTrue =  filebrowser.options.resolveToggle(item);

        assert.deepEqual(resultFalse, m('i.icon-plus', ' '), 'when item is folder and open is false returns with plus sign.');
        assert.deepEqual(resultTrue, m('i.icon-minus', ' '), 'when item is folder and open is true returns with minus sign.');
        assert.equal(resultItemFalse, '', 'when item is folder and open is false returns "".');
        assert.equal(resultItemTrue, '', 'when item is folder and open is false returns "".');
    });

    QUnit.test('_fangornToggleCheck() works', function(assert){
        var folder = filebrowser.grid.createItem({'kind': 'folder', 'name': 'FolderToggleCheck', 'permissions':{edit:true, view:true}}, 1);
        var item = filebrowser.grid.createItem({'kind': 'item', 'name': 'ItemToggleCheck', 'permissions':{edit:true, view:true}}, 1);

        //Testing for Folders
        var publicFolder = filebrowser.options.togglecheck(folder);
        folder.data.permissions.view = false;
        var privateFolder = filebrowser.options.togglecheck(folder);

        //Testing for Items
        var publicItem = filebrowser.options.togglecheck(item);
        item.data.permissions.view = false;
        var privateItem = filebrowser.options.togglecheck(item);

        assert.ok(publicFolder, 'When item is folder and view is true, returns true');
        assert.ok(publicItem, 'When item is item and view is true, returns true');
        assert.deepEqual(privateFolder, false, 'When item is folder and view is true, returns true');
        assert.deepEqual(privateItem, false, 'When item is item and view is true, returns true');
    });

    QUnit.test('_fangornResolveUploadUrl() works', function(assert){
        var folder = filebrowser.grid.createItem({'kind': 'folder', 'name': 'FolderResolveUploadUrl', 'permissions':{edit:true, view:true}}, 1);
        var item = filebrowser.grid.createItem({'kind': 'item', 'name': 'ItemResolveUploadUrl', 'permissions':{edit:true, view:true}}, 1);

        //Testing for Folders
        folder.data.urls = {};
        var folderNoUrlUploadUrl = filebrowser.options.resolveUploadUrl(folder);
        folder.data.urls = {upload:""};
        folder.data.urls.upload = "www.osf.io";
        var folderUploadUrl = filebrowser.options.resolveUploadUrl(folder);
        folder.data.addon = "s3";
        var folderGitUploadUrl = filebrowser.options.resolveUploadUrl(folder);

        //Testing for Items
        item.data.urls = {};
        var itemNoUrlUploadUrl = filebrowser.options.resolveUploadUrl(item);
        item.data.urls = {upload:""};
        item.data.urls.upload = "www.osf.io";
        var itemUploadUrl = filebrowser.options.resolveUploadUrl(item);
        item.data.addon = "s3";
        var itemGitUploadUrl = filebrowser.options.resolveUploadUrl(item);

        assert.deepEqual(folderNoUrlUploadUrl, undefined, 'When item is folder and there is no upload URL, returns undefined');
        assert.deepEqual(folderUploadUrl, folder.data.urls.upload, 'When item is folder and there is an upload URL, returns with url of item');
        assert.deepEqual(folderGitUploadUrl, folder.data.urls.upload, 'When item is folder and there is an addon upload URL, returns with url of addon');
        assert.deepEqual(itemNoUrlUploadUrl, undefined, 'When item is item and there is no upload URL, returns undefined');
        assert.deepEqual(itemUploadUrl, folder.data.urls.upload, 'When item is item and there is no upload URL, returns null(?)');
        assert.deepEqual(itemGitUploadUrl, folder.data.urls.upload, 'When item is item and there is no upload URL, returns null(?)');
    });

    //QUnit.test('_fangornMouseOverRow() works', function(assert){});
    //QUnit.test('_fangornUploadProgress() works', function(assert){});

    /*QUnit.test('_fangornSending() works', function(assert){
        var folder = filebrowser.grid.createItem({'kind': folder, 'name': 'FolderSending', 'permissions':{edit:true, view:true}}, 1);
        var item = filebrowser.grid.createItem({'kind': item, 'name': 'ItemSending', 'permissions':{edit:true, view:true}}, 1);

        //Testing for Folders

        //Testing for Items
        var itemSending = filebrowser.options.dropzoneEvents.sending(filebrowser.grid, item);

        assert.deepEqual(itemSending, null, 'When file is item, returns null');
    });*/

    //QUnit.test('_fangornAddedFile works', function(assert){});
    //QUnit.test('_fangornDragOver works', function(assert){});
    //QUnit.test('_fangornComplete works', function(assert){});
    //QUnit.test('_fangornDropzoneSuccess works', function(assert){});
    //QUnit.test('_fangornDropzoneSuccess works', function(assert){});
    //QUnit.test('_fangornDropzoneError works', function(assert){});
    //QUnit.test('_uploadEvent works', function(assert){});
    //QUnit.test('_downloadEvent works', function(assert){});
    //QUnit.test('_removeEvent works', function(assert){});
    QUnit.test('_fangornResolveLazyLoad works', function(assert){
        var folder = filebrowser.grid.createItem({'kind': 'folder', 'name': 'FolderResolveLazyLoad', 'permissions':{edit:true, view:true}}, 1);
        var item = filebrowser.grid.createItem({'kind': 'item', 'name': 'ItemResolveLazyLoad', 'permissions':{edit:true, view:true}}, 1);

        //Testing for Folders
        folder.data.urls = {};
        var folderNoFetchUrl = filebrowser.options.resolveLazyloadUrl(folder);
        folder.data.urls = {fetch:""};
        folder.data.urls.fetch = "www.osf.io";
        var folderFetchUrl = filebrowser.options.resolveLazyloadUrl(folder);
        folder.data.addon = "github";
        var folderGitFetchUrl = filebrowser.options.resolveLazyloadUrl(folder);

        //Testing for Items
        item.data.urls = {};
        var itemNoFetchUrl = filebrowser.options.resolveLazyloadUrl(item);
        item.data.urls = {fetch:""};
        item.data.urls.fetch = "www.osf.io";
        var itemFetchUrl = filebrowser.options.resolveLazyloadUrl(item);
        item.data.addon = "github";
        var itemGitFetchUrl = filebrowser.options.resolveLazyloadUrl(item);

        assert.deepEqual(folderNoFetchUrl, false, 'When item is folder and there is no fetch URL, returns false');
        assert.deepEqual(folderFetchUrl, folder.data.urls.fetch, 'When item is folder and there is a fetch URL but no addon, returns folder.data.urls.fetch');
        assert.deepEqual(folderGitFetchUrl, folder.data.urls.fetch, 'When item is folder and there is an addon fetch URL, returns with url of addon');
        assert.deepEqual(itemNoFetchUrl, false, 'When item is item and there is no fetch URL, returns false');
        //assert.deepEqual(itemFetchUrl, false, 'When item is item and there is no fetch URL, returns false');
        //assert.deepEqual(itemGitFetchUrl, false, 'When item is item and there is no fetch URL, returns false');
    });
    QUnit.test('_addcheck & _fangornFileExists works', function(assert){
        var folder = filebrowser.grid.createItem({'kind': 'folder', 'name': 'FolderFileExists', 'permissions':{edit:true, view:true}}, 1);
        var item = filebrowser.grid.createItem({'kind': 'item', 'name': 'ItemFileExists.txt', 'permissions':{edit:true, view:true}}, 1);
        var file1 = filebrowser.grid.createItem({'kind': 'item', 'name': 'ItemFileExists1.txt', 'permissions':{edit:true, view:true}}, 1);
        var file2 = filebrowser.grid.createItem({'kind': 'item', 'name': 'ItemFileDoesNotExist.txt', 'permissions':{edit:true, view:true}}, 1);
        folder.add(item);

        //console.log("folder",folder);

        var fileExists = filebrowser.options.addcheck(filebrowser.grid, item, file1);
        var fileDoesNotExist = filebrowser.options.addcheck(filebrowser.grid, item, file2);

        item.data.permissions.edit = false;
        var privateFolderExists = filebrowser.options.addcheck(filebrowser.grid, item, file1);
        var privateFolderDoesNotExist = filebrowser.options.addcheck(filebrowser.grid, item, file2);

        assert.ok(fileExists, 'When item is item and there is another file of the same name in the folder, returns true');
        assert.ok(fileDoesNotExist, 'When item is item and there is another file with a different name in the folder, returns false. Addcheck however returns true');
        assert.deepEqual(privateFolderExists, false, 'When item is item and there another file of the same name in a private folder, returns false');
        assert.deepEqual(privateFolderDoesNotExist, false, 'When item is item and there is another file with a different name in a private folder, returns false');
    });
    //QUnit.test('_fangornLazyLoadError works', function(assert){});
    QUnit.test('_fangornUploadMethod works', function(assert){
        var folder = filebrowser.grid.createItem({'kind': 'folder', 'name': 'FolderUploadMethod', 'permissions':{edit:true, view:true}}, 1);
        var item = filebrowser.grid.createItem({'kind': 'item', 'name': 'ItemUploadMethod.txt', 'permissions':{edit:true, view:true}}, 1);

        var itemUploadMethod = filebrowser.options.resolveUploadMethod(item);
        item.data.addon = "s3";
        var itemS3UploadMethod = filebrowser.options.resolveUploadMethod(item);

        assert.deepEqual(itemUploadMethod, 'POST', 'When item is item and is not an addon the upload method is set as POST');
        assert.deepEqual(itemS3UploadMethod, 'PUT', 'When item is item and is a s3 addon the upload method is set as PUT');
    });
    //QUnit.test('_fangornResolveRows works', function(assert){});

    QUnit.test('_fangornColumnTitles works', function(assert){
        var columns = [];
        columns.push({
                title: 'Name',
                width : '50%',
                sort : true,
                sortType : 'text'
            },
            {
                title : 'Actions',
                width : '25%',
                sort : false
            },
            {
                title : 'Downloads',
                width : '25%',
                sort : false
            });

        var myColumns = filebrowser.options.columnTitles();

        assert.deepEqual(myColumns,columns);
    });

