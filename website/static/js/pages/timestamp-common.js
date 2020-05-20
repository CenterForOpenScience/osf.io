'use strict';

var $ = require('jquery');
var List = require('list.js');
var $osf = require('js/osfHelpers');
var vkbeautify = require('vkbeautify');
var taskStatusUpdaterIntervalId = null;
var taskStatusUrl = null;

var _ = require('js/rdmGettext')._;

var datepicker = require('js/datepicker');

var dateString = new Date().toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
}).replace(/[/ :年月日]/g, '').replace(/\u200E/g, '');

var DOWNLOAD_FILENAME;
// called on rdm-timestampadd-page.js and timestamp-page.js/
// argument should be 'web' or 'admin'
var setWebOrAdmin = function(webOrAdminString) {
    DOWNLOAD_FILENAME = webOrAdminString + '_' + dateString + '_' + 'timestamp_errors';
};

var HEADERS_ORDER = [
    'timestampId', 'fileGuidResource', 'fileGuidLabel', 'fileGuid', 'fileNameResource',
    'fileNameLabel', 'fileCreationDate', 'fileModificationDate', 'fileByteSize',
    'fileVersion', 'projectGuidResource', 'projectGuidLabel', 'projectGuid', 'userGuidResource',
    'userGuidLabel', 'userNameResource', 'userNameLabel', 'mail', 'orgIdResource', 'orgIdLabel',
    'orgNameResource', 'orgNameLabel', 'userGuid', 'tsIdLabel', 'tsVerificationStatus',
    'latestTsVerificationDate'
];
var HEADER_NAMES = {
    timestampId: 'Timestamp ID',
    fileGuidResource: 'File GUID Resource',
    fileGuidLabel: 'File GUID Label',
    fileGuid: 'File GUID',
    fileNameResource: 'File Name Resource',
    fileNameLabel: 'File Name Label',
    fileCreationDate: 'File Creation Date',
    fileModificationDate: 'File Modification Date',
    fileByteSize: 'File ByteSize',
    fileVersion: 'File Version',
    projectGuidResource: 'Project GUID Resource',
    projectGuidLabel: 'Project GUID Label',
    projectGuid: 'Project GUID',
    userGuidResource: 'User GUID Resource',
    userGuidLabel: 'User GUID Label',
    userNameResource: 'User Name Resource',
    userNameLabel: 'User Name Label',
    mail: 'Mail',
    orgIdResource: 'Organization ID Resource',
    orgIdLabel: 'Organization ID Label',
    orgNameResource: 'Organization Name Resource',
    orgNameLabel: 'Organization Name Label',
    userGuid: 'User GUID',
    tsIdLabel: 'Timestamp ID Label',
    tsVerificationStatus: 'Timestamp Verification Status',
    latestTsVerificationDate: 'Latest Timestamp Verification Date'
};
var RESOURCE_HOST = 'rdf.rdm.nii.ac.jp';

var TIMESTAMP_LIST_OBJECT = new List('timestamp-form', {
    valueNames: [
        'provider',
        {name: 'creator_name', attr: 'value'},
        {name: 'creator_email', attr: 'value'},
        {name: 'creator_id', attr: 'value'},
        {name: 'file_path', attr: 'value'},
        {name: 'file_id', attr: 'value'},
        {name: 'file_create_date_on_upload', attr: 'value'},
        {name: 'file_create_date_on_verify', attr: 'value'},
        {name: 'file_modify_date_on_upload', attr: 'value'},
        {name: 'file_modify_date_on_verify', attr: 'value'},
        {name: 'file_size_on_upload', attr: 'value'},
        {name: 'file_size_on_verify', attr: 'value'},
        {name: 'file_version', attr: 'value'},
        {name: 'project_id', attr: 'value'},
        {name: 'organization_id', attr: 'value'},
        {name: 'organization_name', attr: 'value'},
        {name: 'verify_user_id', attr: 'value'},
        {name: 'verify_user_name', attr: 'value'},
        {name: 'verify_date', attr: 'value'},
        {name: 'verify_result_title', attr: 'value'},
        'verify_user_name_id'
    ],
    page: 10,
    pagination: {
        paginationClass: 'listjs-pagination',
        innerWindow: 3,
        outerWindow: 1
    }
});

TIMESTAMP_LIST_OBJECT.on('updated', function (list) {
    var isFirst = list.i === 1;
    var isLast = list.i > list.matchingItems.length - list.page;

    if (list.items.length > list.page) {
        $('.pagination-wrap').show();
    } else {
        $('.pagination-wrap').hide();
    }

    $('.pagination-prev.disabled, .pagination-next.disabled').removeClass('disabled');
    if (isFirst) {
        $('.pagination-prev').addClass('disabled');
    }
    if (isLast) {
        $('.pagination-next').addClass('disabled');
    }
});

$('.pagination-prev').click(function () {
    $('.listjs-pagination .active').prev().trigger('click');
    return false;
});

$('.pagination-next').click(function () {
    $('.listjs-pagination .active').next().trigger('click');
    return false;
});

$('#pageLength').change(function () {
    TIMESTAMP_LIST_OBJECT.page = $(this).val();
    TIMESTAMP_LIST_OBJECT.update();
    $('.listjs-pagination li').first().trigger('click');
});

$('#addTimestampAllCheck').on('change', function () {
    var checkAll = this.checked;
    TIMESTAMP_LIST_OBJECT.items.map(function (item) {
        $(item.elm).find('#addTimestampCheck').prop('checked', checkAll);
    });
});

function newLine () {
    if (window.navigator.userAgent.indexOf('Windows NT') !== -1) {
        return '\r\n';
    }
    return '\n';
}

var NEW_LINE = newLine();

function loadingAnimation (activated) {
    $('#loading-row').toggle(activated);
    $('#pagination-row').toggle(!activated);
    $('#timestamp-table-row').toggle(!activated);
    $('#download-row').toggle(!activated);

    $('#btn-verify').attr('disabled', activated);
    $('#btn-addtimestamp').attr('disabled', activated);
    $('#btn-cancel').attr('disabled', !activated);
}

var verify = function (params) {
    loadingAnimation(true);

    // Get files list
    $.ajax({
        url: params.urlVerify,
        data: {},
        dataType: 'json',
        method: 'POST'
    }).done(function () {
        $osf.growl('Timestamp', _('A verify request is being processed!'), 'success');
        taskStatusUpdaterIntervalId = setInterval(taskStatusUpdater, 1500);
    }).fail(function () {
        $osf.growl('Timestamp', _('Something went wrong with the Verify request.'), 'danger');
    });
};

var add = function (param) {
    var fileList = TIMESTAMP_LIST_OBJECT.items.filter(function (item) {
        var checkbox = item.elm.querySelector('[type=checkbox]');
        if (checkbox) {
            return checkbox.checked;
        }
        return false;
    }).map(function (item) {
        return item.values();
    });

    if (fileList.length === 0) {
        $osf.growl('Timestamp', _('Using the checkbox, please select the files to request timestamp.'), 'danger');
        return false;
    }

    loadingAnimation(true);
    var postData = [];

    for (var i = 0; i < fileList.length; i++) {
        postData.push({
            'provider': fileList[i].provider,
            'file_id': fileList[i].file_id,
            'file_path': fileList[i].file_path,
            'file_version': fileList[i].file_version
        });
    }

    $.ajax({
        type: 'POST',
        url: param.url,
        data: JSON.stringify(postData),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json'
    }).done(function () {
        $osf.growl('Timestamp', _('Timestamp is being added to the selected files!'), 'success');
        taskStatusUpdaterIntervalId = setInterval(taskStatusUpdater, 1500);
    }).fail(function () {
        $osf.growl('Timestamp', _('Something went wrong with the Request Trusted Timestamp request.'), 'danger');
    });
};

var cancel = function (url) {
    $osf.growl('Timestamp', _('The task has been cancelled.'), 'info');
    $('#btn-cancel').attr('disabled', true);
    $.ajax({
        url: url,
        method: 'POST'
    }).done(function (result) {
        if (result.success === true) {
            $('#btn-cancel').attr('disabled', true);
        } else {
            $osf.growl('Timestamp', _('The task already finished.'), 'info');
        }
    }).fail(function () {
        $osf.growl('Timestamp', _('Something went wrong in the cancel request.'), 'danger');
    });
};

var download = function (url) {
    var fileFormat = $('#fileFormat').val();
    var fileList = TIMESTAMP_LIST_OBJECT.items.filter(function (item) {
        var checkbox = item.elm.querySelector('[type=checkbox]');
        if (checkbox) {
            return checkbox.checked;
        }
        return false;
    }).map(function (item) {
        item = item.values();

        var filePathArr = item.file_path.split('/');
        var fileName = filePathArr[filePathArr.length - 1];

        var userId = item.verify_user_id ? item.verify_user_id : 'Unknown';
        var tsDate = item.verify_date ? item.verify_date.replace(' ', '_').replace(/[/]/g, '-').replace(/:/g, '') : 'Unknown';
        var fileCreationDate = item.file_create_date_on_verify ? item.file_create_date_on_verify.replace(' ', '_').replace(/[/]/g, '-').replace(/:/g, '') : null;
        var fileModificationDate = item.file_modify_date_on_verify ? item.file_modify_date_on_verify.replace(' ', '_').replace(/[/]/g, '-').replace(/:/g, '') : null;

        return {
            timestampId: 'https://' + RESOURCE_HOST + '/resource/ts/' + item.project_id + '/' + item.file_id + '/' + userId + '/' + tsDate,
            fileGuidResource: 'https://' + RESOURCE_HOST + '/resource/file/' + item.file_id,
            fileGuidLabel: {text: 'FILE:' + item.file_id, lang: 'en'},
            fileGuid: 'https://' + RESOURCE_HOST + '/' + item.file_id,
            fileNameResource: 'https://' + RESOURCE_HOST + '/resource/file/' + encodeURIComponent(fileName),
            fileNameLabel: {text: fileName, lang: 'en'},
            fileCreationDate: fileCreationDate,
            fileModificationDate: fileModificationDate,
            fileByteSize: item.file_size_on_verify,
            fileVersion: item.file_version,
            projectGuidResource: 'https://' + RESOURCE_HOST + '/resource/project/' + item.project_id,
            projectGuidLabel: {text: 'PROJ:' + item.project_id, lang: 'en'},
            projectGuid: 'https://' + RESOURCE_HOST + '/' + item.project_id,
            userGuidResource: item.creator_id ? 'https://' + RESOURCE_HOST + '/resource/user/' + item.creator_id : null,
            userGuidLabel: item.creator_id ? {text: 'USER:' + item.creator_id, lang: 'en'} : null,
            userNameResource: item.creator_name ? 'https://' + RESOURCE_HOST + '/resource/user/' + encodeURIComponent(item.creator_name) : null,
            userNameLabel: item.creator_name ? {text: item.creator_name, lang: 'en'} : null,
            mail: item.creator_email,
            orgIdResource: item.organization_id ? 'https://' + RESOURCE_HOST + '/resource/org/' + item.organization_id : null,
            orgIdLabel: item.organization_id ? {text: 'ORG:' + item.organization_id, lang: 'en'} : null,
            orgNameResource: item.organization_name ? 'https://' + RESOURCE_HOST + '/resource/org/' + encodeURIComponent(item.organization_name) : null,
            orgNameLabel: item.organization_name ? {text: item.organization_name, lang: 'en'} : null,
            userGuid: item.creator_id ? 'https://' + RESOURCE_HOST + '/' + item.creator_id : null,
            tsIdLabel: {text: 'TS:' + item.project_id + '/' + item.file_id + '/' + userId + '/' + tsDate, lang: 'en'},
            tsVerificationStatus: item.verify_result_title,
            latestTsVerificationDate: tsDate
        };
    });

    if (fileList.length === 0) {
        $osf.growl('Timestamp', _('Using the checkbox, please select the files to download.'), 'danger');
        return false;
    }

    var fileFormatStr;
    var fileContent;
    switch (fileFormat) {
        case 'csv':
            fileFormatStr = 'CSV';
            fileContent = generateCsv(fileList, HEADERS_ORDER, HEADER_NAMES);
            saveTextFile(DOWNLOAD_FILENAME + '.csv', fileContent);
            break;
        case 'json-ld':
            fileFormatStr = 'JSON/LD';
            fileContent = generateJson(fileList);
            saveTextFile(DOWNLOAD_FILENAME + '.json', fileContent);
            break;
        case 'rdf-xml':
            fileFormatStr = 'RDF/XML';
            fileContent = generateRdf(fileList);
            saveTextFile(DOWNLOAD_FILENAME + '.rdf', fileContent);
            break;
    }

    var postData = {
        'file_format': fileFormatStr
    };
    $.ajax({
        type: 'POST',
        url: url,
        data: JSON.stringify(postData),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json'
    }).done(function (result) {
    }).fail(function () {
        $osf.growl('Timestamp', _('Failed to log "downloaded errors" into Recent Activity'), 'danger');
    });
};

function generateCsv(fileList, headersOrder, headerNames) {
    var content = '';

    // Generate header
    content += headersOrder.map(function (headerName) {
        return headerNames[headerName];
    }).join(',') + NEW_LINE;

    // Generate content
    content += fileList.map(function (file) {
        return headersOrder.map(function (headerName) {
            if (file[headerName] === null) {
                return 'Unknown';
            }
            if (typeof file[headerName] === 'object') {
                return '"""' + file[headerName].text + '""@' + file[headerName].lang + '"';
            }
            if (/["|,]/.test(file[headerName])) {
                return '"' + file[headerName].replace(/"/g, '""') + '"';
            }
            return file[headerName];
        }).join(',');
    }).join(NEW_LINE);

    return content;
}

function generateJson(fileList) {
    // Update headers as defined in HEADERS_NAME
    fileList = fileList.map(function (file) {
        return [
            {
                '@id': file.projectGuidResource,
                '@type': 'foaf:Project',
                'rdfs:label': {
                    '@language': file.projectGuidLabel.lang,
                    '@value': file.projectGuidLabel.text
                },
                'rdfs:seeAlso': {
                    '@id': file.projectGuid
                }
            },
            {
                '@id': file.userNameResource ? file.userNameResource : 'Unknown',
                '@type': 'foaf:Person',
                'rdfs:label': file.userNameLabel ? {
                    '@language': file.userNameLabel.lang,
                    '@value': file.userNameLabel.text
                } : 'Unknown'
            },
            {
                '@id': file.orgIdResource ? file.orgIdResource : 'Unknown',
                '@type': 'org:Organization',
                'rdfs:label': file.orgIdLabel ? {
                    '@language': file.orgIdLabel.lang,
                    '@value': file.orgIdLabel.text
                } : 'Unknown'
            },
            {
                '@id': file.orgNameResource ? file.orgNameResource : 'Unknown',
                '@type': 'frapo:organization',
                'rdfs:label': file.orgNameLabel ? {
                    '@language': file.orgNameLabel.lang,
                    '@value': file.orgNameLabel.text
                } : 'Unknown'
            },
            {
                '@id': file.fileGuidResource,
                '@type': 'sio:000396',
                'dcat:bytes': file.fileByteSize,
                'dcterms:created': {
                    '@type': 'xsd:dateTime',
                    '@value': file.fileCreationDate ? file.fileCreationDate : 'Unknown'
                },
                'dcterms:hasVersion': {
                    '@type': 'xsd:int',
                    '@value': file.file_version
                },
                'dcterms:modified': {
                    '@type': 'xsd:dateTime',
                    '@value': file.fileModificationDate ? file.fileModificationDate : 'Unknown'
                },
                'dcterms:title': {
                    '@id': file.fileNameResource
                },
                'rdfs:label': {
                    '@language': file.fileGuidLabel.lang,
                    '@value': file.fileGuidLabel.text
                },
                'rdfs:seeAlso': {
                    '@id': file.fileGuid
                }
            },
            {
                '@id': file.fileNameResource,
                'rdfs:label': {
                    '@language': file.fileNameLabel.leng,
                    '@value': file.fileNameLabel.text
                }
            },
            {
                '@id': file.timestampId,
                '@type': 'dcat:Dataset',
                'dcterms:identifier': {
                    '@id': file.fileGuidResource
                },
                'frapo:hasProjectIdentifier': {
                    '@id': file.projectGuidResource
                },
                'rdfs:label': {
                    '@language': file.tsIdLabel.lang,
                    '@value': file.tsIdLabel.text
                },
                'sem:hasLatestEndTimeStamp': file.latestTsVerificationDate,
                'sem:hasTimestamp': file.tsVerificationStatus,
                'sioc:id': {
                    '@id': file.userGuidResource ? file.userGuidResource : 'Unknown'
                }
            },
            {
                '@id': file.userGuidResource ? file.userGuidResource : 'Unknown',
                '@type': 'foaf:Agent',
                'dcterms:creator': {
                    '@id': file.userNameResource ? file.userNameResource : 'Unknown'
                },
                'org:memberOf': {
                    '@id': file.orgIdResource ? file.orgIdResource : 'Unknown'
                },
                'rdfs:label': file.userGuidLabel ? {
                    '@language': file.userGuidLabel.lang,
                    '@value': file.userGuidLabel.text
                } : 'Unknown',
                'rdfs:seeAlso': {
                    '@id': file.userGuid ? file.userGuid : 'Unknown'
                },
                'vcard:hasEmail': file.mail ? file.mail : 'Unknown'
            }
        ];
    });

    fileList = fileList.reduce(function(a, b) {return a.concat(b);}, []);

    var JSONFile = {
        '@context': {
            'dcat': 'http://www.w3.org/ns/dcat#',
            'dcterms': 'http://purl.org/dc/terms/',
            'foaf': 'http://xmlns.com/foaf/0.1/',
            'frapo': 'http://purl.org/cerif/frapo/',
            'org': 'http://www.w3.org/ns/org#',
            'owl': 'http://www.w3.org/2002/07/owl#',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'rdmr': 'https://' + RESOURCE_HOST + '/resource/',
            'schema': 'http://schema.org/',
            'sem': 'http://semanticweb.cs.vu.nl/2009/11/sem/',
            'sio': 'http://semanticscience.org/resource/',
            'sioc': 'http://rdfs.org/sioc/ns#',
            'vcard': 'http://www.w3.org/2006/vcard/ns#',
            'xsd': 'http://www.w3.org/2001/XMLSchema#'
        },
        '@graph': fileList,
    };

    // Generate content
    return vkbeautify.json(JSON.stringify(JSONFile)).replace(/\n/g, NEW_LINE);
}

function generateRdf (fileList) {
    var i, key;
    var doc = document.implementation.createDocument('http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'rdf:RDF', null);

    // Auxiliary functions for generating the RDF file
    var createEl = function (doc, elementName, attributes, text) {
        var element = doc.createElement(elementName);
        if (attributes) {
            var i, attr, attrName;
            for (i = 0; i < attributes.length; i++) {
                attr = attributes[i];
                for (attrName in attr) {
                    if (attr.hasOwnProperty(attrName)) {
                        element.setAttribute(attrName, attr[attrName]);
                    }
                }
            }
        }
        if (text) {
            element.textContent = text;
        }
        return element;
    };
    var linkChildren = function (element, childrenArray) {
        if (!childrenArray) {
            return;
        }
        var i, child;
        for (i = 0; i < childrenArray.length; i++) {
            child = childrenArray[i];
            linkChildren(child.element, child.children);
            element.appendChild(child.element);
        }
    };

    var namespaces = [
        {schema: 'http://schema.org/'},
        {rdmr: 'https://' + RESOURCE_HOST + '/resource/'},
        {owl: 'http://www.w3.org/2002/07/owl#'},
        {org: 'http://www.w3.org/ns/org#'},
        {frapo: 'http://purl.org/cerif/frapo/'},
        {xsd: 'http://www.w3.org/2001/XMLSchema#'},
        {rdfs: 'http://www.w3.org/2000/01/rdf-schema#'},
        {vcard: 'http://www.w3.org/2006/vcard/ns#'},
        {rdf: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'},
        {sio: 'http://semanticscience.org/resource/'},
        {dcterms: 'http://purl.org/dc/terms/'},
        {sem: 'http://semanticweb.cs.vu.nl/2009/11/sem/'},
        {dcat: 'http://www.w3.org/ns/dcat#'},
        {foaf: 'http://xmlns.com/foaf/0.1/'},
        {sioc: 'http://rdfs.org/sioc/ns#'},
    ];

    // Add namespaces to root (rdf)
    for (i = 0; i < namespaces.length; i++) {
        for (key in namespaces[i]) {
            if (namespaces[i].hasOwnProperty(key)) {
                doc.documentElement.setAttribute('xmlns:' + key, namespaces[i][key]);
            }
        }
    }

    for (i = 0; i < fileList.length; i++) {
        var item = fileList[i];

        var rdfElements = [
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.timestampId}]),
                children: [
                    {element: createEl(doc, 'rdf:type', [{'rdf:resource': 'http://www.w3.org/ns/dcat#Dataset'}])}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.fileGuidResource}]),
                children: [
                    {element: createEl(doc, 'rdf:type', [{'rdf:resource': 'http://semanticscience.org/resource/SIO_000396'}])},
                    {element: createEl(doc, 'rdfs:seeAlso', [{'rdf:resource': item.fileGuid}])},
                    {element: createEl(doc, 'rdfs:label', [{'xml:lang': item.fileGuidLabel.lang}], item.fileGuidLabel.text)}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.fileNameResource}]),
                children: [
                    {element: createEl(doc, 'rdfs:label', [{'xml:lang': item.fileNameLabel.lang}], item.fileNameLabel.text)}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.fileGuidResource}]),
                children: [
                    {element: createEl(doc, 'dcterms:title', [{'rdf:resource': item.fileNameResource}])},
                    {element: createEl(doc, 'dcterms:created', [{'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#dateTime'}], item.fileCreationDate ? item.fileCreationDate : 'Unknown')},
                    {element: createEl(doc, 'dcterms:modified', [{'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#dateTime'}], item.fileModificationDate ? item.fileModificationDate : 'Unknown')},
                    {element: createEl(doc, 'dcat:bytes', [{'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#double'}], item.fileByteSize ? item.fileByteSize : 'Unknown')},
                    {element: createEl(doc, 'dcterms:hasVersion', [{'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#int'}], item.fileVersion ? item.fileVersion : 'Unknown')}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.timestampId}]),
                children: [
                    {element: createEl(doc, 'dcterms:identifier', [{'rdf:resource': item.fileGuidResource}])}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.projectGuidResource}]),
                children: [
                    {element: createEl(doc, 'rdf:type', [{'rdf:resource': 'http://xmlns.com/foaf/0.1/Project'}])},
                    {element: createEl(doc, 'rdfs:seeAlso', [{'rdf:resource': item.projectGuid}])},
                    {element: createEl(doc, 'rdfs:label', [{'xml:lang': item.projectGuidLabel.lang}], item.projectGuidLabel.text)}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.timestampId}]),
                children: [
                    {element: createEl(doc, 'frapo:hasProjectIdentifier', [{'rdf:resource': item.projectGuidResource}])}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.userGuidResource ? item.userGuidResource : 'Unknown'}]),
                children: [
                    {element: createEl(doc, 'rdf:type', [{'rdf:resource': 'http://xmlns.com/foaf/0.1/Agent'}])},
                    {element: createEl(doc, 'rdfs:label', item.userGuidLabel ? [{'xml:lang': item.userGuidLabel.lang}] : null, item.userGuidLabel ? item.userGuidLabel.text : 'Unknown')}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.userNameResource ? item.userNameResource : 'Unknown'}]),
                children: [
                    {element: createEl(doc, 'rdf:type', [{'rdf:resource': 'http://xmlns.com/foaf/0.1/Person'}])},
                    {element: createEl(doc, 'rdfs:label', item.userNameLabel ? [{'xml:lang': item.userNameLabel.lang}] : null, item.userNameLabel ? item.userNameLabel.text : 'Unknown')}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.userGuidResource ? item.userGuidResource : 'Unknown'}]),
                children: [
                    {element: createEl(doc, 'dcterms:creator', [{'rdf:resource': item.userNameResource ? item.userNameResource : 'Unknown'}])},
                    {element: createEl(doc, 'vcard:hasEmail', null, item.mail ? item.mail : 'Unknown')}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.orgIdResource ? item.orgIdResource : 'Unknown'}]),
                children: [
                    {element: createEl(doc, 'rdf:type', [{'rdf:resource': 'http://www.w3.org/ns/org#Organization'}])},
                    {element: createEl(doc, 'rdfs:label', item.orgIdLabel ? [{'xml:lang': item.orgIdLabel.lang}] : null, item.orgIdLabel ? item.orgIdLabel.text : 'Unknown')},
                    {element: createEl(doc, 'frapo:organization', [{'rdf:resource': item.orgNameResource ? item.orgNameResource : 'Unknown'}])}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.orgNameResource ? item.orgNameResource : 'Unknown'}]),
                children: [
                    {element: createEl(doc, 'rdfs:label', item.orgNameLabel ? [{'xml:lang': item.orgNameLabel.lang}] : null, item.orgNameLabel ? item.orgNameLabel.text : 'Unknown')}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.userGuid ? item.userGuid : 'Unknown'}]),
                children: [
                    {element: createEl(doc, 'org:memberOf', [{'rdf:resource': item.orgIdResource ? item.orgIdResource : 'Unknown'}])},
                    {element: createEl(doc, 'rdfs:seeAlso', [{'rdf:resource': item.userGuid ? item.userGuid : 'Unknown'}])}
                ]
            },
            {
                element: createEl(doc, 'rdf:Description', [{'rdf:about': item.timestampId}]),
                children: [
                    {element: createEl(doc, 'sioc:id', [{'rdf:resource': item.userGuidResource ? item.userGuidResource : 'Unknown'}])},
                    {element: createEl(doc, 'rdfs:label', [{'xml:lang': item.tsIdLabel.lang}], item.tsIdLabel.text)},
                    {element: createEl(doc, 'sem:hasTimestamp', null, item.tsVerificationStatus)},
                    {element: createEl(doc, 'sem:hasLatestEndTimeStamp', null, item.latestTsVerificationDate)}
                ]
            }
        ];

        linkChildren(doc.documentElement, rdfElements);
    }

    var serializer = new XMLSerializer();
    return vkbeautify.xml(serializer.serializeToString(doc).replace(/xmlns:NS\d+="" NS\d+:/g, '')).replace(/\n/g, NEW_LINE);
}

function saveTextFile(filename, content) {
    if (window.navigator.msSaveOrOpenBlob) {
        var blob = new Blob([content], {type: 'text/plain; charset=utf-8'});
        window.navigator.msSaveOrOpenBlob(blob, filename);
    }
    else {
        var element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain; charset=utf-8,' + encodeURIComponent(content));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }
}

function initList() {

    // sort buttons code

    // this is necessary because javascript doesn't provide the default compare function it uses
    var defaultSort = function (a, b) {
        if (a === b) {return 0;}
        else {
            var list = [a, b];
            list.sort();
            return list.indexOf(a) === 0 ? -1 : 1;
        }
    };

    var sortFunction = function(a, b, options) {
        if (a.values().provider !== b.values().provider) {
            return defaultSort(a.values().provider, b.values().provider);
        }
        else {
            return defaultSort(a.values()[options.valueName], b.values()[options.valueName]);
        }
    };

    var propertyNames = ['provider', 'file_path', 'verify_user_name_id', 'verify_date', 'verify_result_title'];
    var clickSortUpElements = propertyNames.map(function(property_name) {
        return 'sort_up_' + property_name;
    }).map(function(click_sort_name) {
        return document.getElementById(click_sort_name);
    });

    var propertyToUpElement = {};
    propertyNames.forEach(function(propertyName, i) {
        propertyToUpElement[propertyName] = clickSortUpElements[i];
    });

    var clickSortDownElements = propertyNames.map(function(property_name) {
        return 'sort_down_' + property_name;
    }).map(function(click_sort_name) {
        return document.getElementById(click_sort_name);
    });

    var propertyToDownElement = {};
    propertyNames.forEach(function(propertyName, i) {
        propertyToDownElement[propertyName] = clickSortDownElements[i];
    });

    for (var upPropertyName in propertyToUpElement) {
        var clickSortUpElement = propertyToUpElement[upPropertyName];
        // closure to make sure propertyName is in scope at click time
        clickSortUpElement.addEventListener('click', (function(propertyName, clickSortUpElements) {
            return function(event) {

                clickSortUpElements.forEach(function(element) {
                    // written this way to ensure it works with IE
                    element.classList.add('tb-sort-inactive');
                });

                clickSortDownElements.forEach(function(element) {
                    // written this way to ensure it works with IE
                    element.classList.add('tb-sort-inactive');
                });

                TIMESTAMP_LIST_OBJECT.sort(propertyName, {order: 'asc', sortFunction: sortFunction});

                event.target.classList.remove('tb-sort-inactive');

            };
        })(upPropertyName, clickSortUpElements));
    }

    for (var downPropertyName in propertyToDownElement) {
        var clickSortDownElement = propertyToDownElement[downPropertyName];
        // closure to make sure upPropertyName is in scope at click time
        clickSortDownElement.addEventListener('click', (function(upPropertyName, clickSortDownElements) {
            return function(event) {

                clickSortDownElements.forEach(function(element) {
                    // written this way to ensure it works with IE
                    element.classList.add('tb-sort-inactive');
                });

                clickSortUpElements.forEach(function(element) {
                    // written this way to ensure it works with IE
                    element.classList.add('tb-sort-inactive');
                });

                TIMESTAMP_LIST_OBJECT.sort(upPropertyName, {order: 'desc', sortFunction: sortFunction});

                event.target.classList.remove('tb-sort-inactive');

            };
        })(downPropertyName, clickSortDownElements));
    }

    // filter by users and date code

    var userFilterSelect = document.getElementById('userFilterSelect');
    var alreadyAdded = [''];
    var users = TIMESTAMP_LIST_OBJECT.items.map(function(i) {return i.values().verify_user_name_id;});

    if (TIMESTAMP_LIST_OBJECT.items.length > TIMESTAMP_LIST_OBJECT.page) {
        $('.pagination-wrap').show();
    } else {
        $('.pagination-wrap').hide();
    }

    for (var i = 0; i < users.length; i++) {
        var userName = users[i];
        if (alreadyAdded.indexOf(userName) === -1) {
            var option = document.createElement('option');
            option.value = userName;
            option.textContent = userName;
            userFilterSelect.add(option);
            alreadyAdded.push(userName);
        }
    }

    document.getElementById('applyFiltersButton').addEventListener('click', function() {
        var userName = userFilterSelect.value;
        var userNameFilter = function(i) {return !userName || (!i.values().verify_user_name_id || (i.values().verify_user_name_id === userName));};
        var filters = [userNameFilter];
        var dateFilters = [
            {
                element: document.getElementById('startDateFilter'),
                comparator: function(a, b) {return a >= b;}
            },
            {
                element: document.getElementById('endDateFilter'),
                comparator: function(a, b) {return a <= b;}
            },
        ];

        for (var i = 0; i < dateFilters.length; i++) {
            var element = dateFilters[i].element;
            var comparator = dateFilters[i].comparator;
            if (element.value) {
                // closure to prevent different filters getting the same element
                filters.push((function (elementValue, comparator) {
                    return function(i) {
                        // sets the time to midnight, which is the same as dates from the input fields
                        // this is needed to make items appear when the filter is set to the same day
                        var verify_date_day = new Date(i.values().verify_date);
                        verify_date_day.setHours(0, 0, 0, 0);

                        // .replace below gets rid of invisible characters IE inserts
                        var dateComponents = elementValue.replace(/\u200E/g, '').split('-');

                        var year = dateComponents[0];
                        var month = dateComponents[1] - 1; // string starts at 1, parameter starts at 0
                        var day = dateComponents[2];
                        var filter_date_day = new Date(year, month, day);
                        filter_date_day.setHours(0, 0, 0, 0);

                        return !i.values().verify_date || comparator( verify_date_day, filter_date_day );
                    };
                })(element.value, comparator));
            }
        }

        TIMESTAMP_LIST_OBJECT.filter(function (i) {
            return filters.every(function(f) {return f(i);});
        });
    });

    TIMESTAMP_LIST_OBJECT.sort('file_path', {order: 'asc', sortFunction: sortFunction});

}

function initTinyDatePicker() {

    var datePickerIds = ['startDateFilter', 'endDateFilter'];

    datePickerIds.forEach(function(id) {
        var TinyDatePicker = window.TinyDatePicker; // this lets the tests pass
        new TinyDatePicker(document.getElementById(id), {
            format: function(date) {
                var dateString = date.toLocaleDateString('ja-JP', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                }).replace(/[/年月]/g, '-').replace(/日/, '');
                return dateString;
            },
            mode: 'dp-below',
        });
    });

}

function initBootstrapDatePicker() {
    datepicker.mount('#startDateFilter', null);
    datepicker.mount('#endDateFilter', null);
}

function taskStatusUpdater () {
    $.ajax({
        url: taskStatusUrl,
        method: 'POST'
    }).done(function (taskStatus) {
        if (taskStatus.ready) {
            clearInterval(taskStatusUpdaterIntervalId);
            taskStatusUpdaterIntervalId = null;
            window.location.reload(true);
        }
    }).fail(function () {
        $osf.growl('Timestamp', 'Failed to get the current task status.', 'danger');
        clearInterval(taskStatusUpdaterIntervalId);
        taskStatusUpdaterIntervalId = null;
    });
}

function checkHasTaskRunning () {
    var cancelBtnEnabled = $('#btn-cancel').attr('disabled');
    if (!cancelBtnEnabled) {
        taskStatusUpdaterIntervalId = setInterval(taskStatusUpdater, 1500);
    }
}

function init(url) {
    taskStatusUrl = url;
    initList();
    initBootstrapDatePicker();
    checkHasTaskRunning();
}

module.exports = {
    verify: verify,
    add: add,
    cancel: cancel,
    init: init,
    download: download,
    setWebOrAdmin: setWebOrAdmin
};
