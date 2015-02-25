'use strict';

var $ = require('jquery');
var m = require('mithril');
var Raven = require('raven-js');
var Treebeard = require('treebeard');
var citations = require('./citations');
var clipboard = require('./clipboard');

var apaStyle = require('raw!styles/apa.csl');

require('../vendor/bower_components/treebeard/dist/treebeard.css');
require('../css/fangorn.css');

function resolveToggle(item) {
    var toggleMinus = m('i.icon-minus', ' ');
    var togglePlus = m('i.icon-plus', ' ');
    if (item.kind === 'folder') {
        return item.open ? toggleMinus : togglePlus;
    } else {
        return '';
    }
}

function resolveIcon(item) {
    var privateFolder = m('img', {
        src: '/static/img/hgrid/fatcowicons/folder_delete.png'
    });
    var openFolder = m('i.icon-folder-open', ' ');
    var closedFolder = m('i.icon-folder-close', ' ');

    if (item.kind === 'folder') {
        return item.open ? openFolder : closedFolder;
    } else if (item.data.icon) {
        return m('i.fa.' + item.data.icon, ' ');
    } else {
        return m('i.icon-file-alt');
    }
}

var utils = {
    reduce: function(array, dst, fn) {
        for (var i = 0; i < array.length; i++) {
            fn(array[i], dst);
        }
        return dst;
    },
    zip: function(array1, array2) {
        var zipped = [];
        var min = Math.min(array1.length, array2.length);
        for (var i = 0; i < min; i++) {
            zipped.push([array1[i], array2[i]]);
        }
        return zipped;
    }
};

var objectify = function(array, key) {
    key = key || 'id';
    return utils.reduce(
        array, {},
        function(item, acc) {
            return acc[item[key]] = item;
        }
    );
};

var formatResult = function(state) {
    return '<div class="citation-result-title">' + state.title + '</div>';
};

var formatSelection = function(state) {
    return state.title;
};

var mergeConfigs = function() {
    var unloads = [];
    var args = Array.prototype.slice.call(arguments);
    return function(elm, isInit, ctx) {
        for (var i=0; i<args.length; i++) {
            args[i] && args[i](elm, isInit, ctx);
            ctx.onunload && unloads.push(ctx.onunload);
            ctx.onunload = null;
        }
        ctx.onunload = function() {
            for (var i=0; i<unloads.length; i++) {
                unloads[i]();
            }
        };
    };
};

var tooltipConfig = function(elm, isInit, ctx) {
    var $elm = $(elm);
    $elm.tooltip({container: 'body'});
    ctx.onunload = function() {
        $elm.tooltip('destroy');
    };
};

var makeButtons = function(item, col, buttons) {
    return buttons.map(function(button) {
        var self = this;
        return m(
            'a', {
                'data-col': item.id
            }, [
                m(
                    'i', {
                        title: button.tooltip,
                        style: button.style,
                        class: button.css,
                        'data-toggle': 'tooltip',
                        'data-placement': 'bottom',
                        'data-clipboard-text': button.clipboard,
                        config: mergeConfigs(button.config, tooltipConfig),
                        onclick: button.onclick ?
                            function(event) {
                                button.onclick.call(self, event, item, col);
                            } :
                            null
                    },
                    [
                        m(
                            'span', {
                                class: button.icon
                            },
                            button.name
                        )
                    ]
                )
            ]
        );
    });
};

var buildExternalUrl = function(csl) {
    if (csl.URL) {
        return csl.URL;
    } else if (csl.DOI) {
        return 'http://dx.doi.org/' + csl.DOI;
    } else if (csl.PMID) {
        return 'http://www.ncbi.nlm.nih.gov/pubmed/' + csl.PMID;
    }
    return null;
};

var makeClipboardConfig = function(getText) {
    return function(elm, isInit, ctx) {
        var $elm = $(elm);
        if (!elm._client) {
            elm._client = clipboard(elm);
            // Attach `beforecopy` handler to ensure updated clipboard text
            if (getText) {
                elm._client.on('beforecopy', function() {
                    $elm.attr('data-clipboard-text', getText());
                });
            }
        }
        ctx.onunload = function() {
            elm._client && elm._client.destroy();
        };
    };
};

var renderActions = function(item, col) {
    var self = this;
    var buttons = [];
    if (item.kind === 'file') {
        buttons.push({
            name: '',
            icon: 'icon-copy',
            css: 'btn btn-default btn-xs',
            tooltip: 'Copy citation',
            clipboard: self.getCitation(item),
            config: makeClipboardConfig()
        });
        // Add link to external document
        var externalUrl = buildExternalUrl(item.data.csl);
        if (externalUrl) {
            buttons.push({
                name: '',
                icon: 'icon-external-link',
                css: 'btn btn-default btn-xs',
                tooltip: 'View original document',
                onclick: function(event) {
                    window.open(externalUrl);
                }
            });
        }
        // Add link to document on reference management service
        if (item.data.serviceUrl) {
            buttons.push({
                name: '',
                icon: 'icon-link',
                css: 'btn btn-default btn-xs',
                tooltip: 'View on ' + self.provider,
                onclick: function(event) {
                    window.open(item.data.serviceUrl);
                }
            });
        }
    } else if (item.kind === 'folder' && item.open && item.children.length) {
        buttons.push({
            name: '',
            icon: 'icon-copy',
            css: 'btn btn-default btn-xs',
            tooltip: 'Copy citations',
            config: makeClipboardConfig(function() {
                return self.getCitations(item).join('\n');
            })
        });
        buttons.push({
            name: '',
            icon: 'icon-download',
            css: 'btn btn-default btn-xs',
            tooltip: 'Download citations',
            config: function(elm, isInit, ctx) {
                var text = self.getCitations(item).join('\n');
                $(elm).parent('a')
                    .attr('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text))
                    .attr('download', item.data.name + '-' + self.styleName + '.txt');
            }
        });
    }
    return makeButtons(item, col, buttons);
};

var treebeardOptions = {
    rowHeight: 30,
    lazyLoad: true,
    showFilter: false,
    resolveIcon: resolveIcon,
    resolveToggle: resolveToggle,
    lazyLoadPreprocess: function(res) {
        return res.contents;
    },
    columnTitles: function() {
        return [{
            title: 'Citation',
            width: '80%',
            sort: false
        }, {
            title: 'Actions',
            width: '20%',
            sort: false
        }];
    }
};

var CitationGrid = function(provider, gridSelector, styleSelector, apiUrl) {
    var self = this;

    self.provider = provider;
    self.gridSelector = gridSelector;
    self.styleSelector = styleSelector;
    self.apiUrl = apiUrl;

    self.styleName = 'apa';
    self.styleXml = apaStyle;
    self.bibliographies = {};

    self.initTreebeard();
    self.initStyleSelect();
};

CitationGrid.prototype.initTreebeard = function() {
    var self = this;
    var options = $.extend({
            divID: self.gridSelector.replace('#', ''),
            filesData: self.apiUrl,
            resolveLazyloadUrl: function(item) {
                return item.data.urls.fetch;
            },
            // Wrap callback in closure to preserve intended `this`
            resolveRows: function() {
                return self.resolveRowAux.call(self, arguments);
            },
        },
        treebeardOptions
    );
    self.treebeard = new Treebeard(options);
};

CitationGrid.prototype.initStyleSelect = function() {
    var self = this;
    var $input = $(self.styleSelector);
    $input.select2({
        allowClear: false,
        formatResult: formatResult,
        formatSelection: formatSelection,
        placeholder: 'Citation Style (e.g. "APA")',
        minimumInputLength: 1,
        ajax: {
            url: '/api/v1/citations/styles/',
            quietMillis: 200,
            data: function(term, page) {
                return {q: term};
            },
            results: function(data, page) {
                return {results: data.styles};
            },
            cache: true
        }
    }).on('select2-selecting', function(event) {
        var styleUrl = '/static/vendor/bower_components/styles/' + event.val + '.csl';
        $.get(styleUrl).done(function(xml) {
            self.updateStyle(event.val, xml);
        }).fail(function(jqxhr, status, error) {
            Raven.captureMessage('Error while selecting citation style: ' + event.val, {
                url: styleUrl, status: status, error: error
            });
        });
    });
};

CitationGrid.prototype.updateStyle = function(name, xml) {
    this.styleName = name;
    this.styleXml = xml;
    this.bibliographies = {};
    this.treebeard.tbController.redraw();
};

CitationGrid.prototype.makeBibliography = function(folder) {
    var data = objectify(
        folder.children.filter(function(child) {
            return child.kind === 'file';
        }).map(function(child) {
            return child.data.csl;
        })
    );
    var citeproc = citations.makeCiteproc(this.styleXml, data, 'text');
    var bibliography = citeproc.makeBibliography();
    if (bibliography[0].entry_ids) {
        return utils.reduce(
            utils.zip(bibliography[0].entry_ids, bibliography[1]), {},
            function(pair, acc) {
                return acc[pair[0][0]] = pair[1];
            }
        );
    }
    return {};
};

CitationGrid.prototype.getBibliography = function(folder) {
    this.bibliographies[folder.id] = this.bibliographies[folder.id] || this.makeBibliography(folder);
    return this.bibliographies[folder.id];
};

CitationGrid.prototype.getCitation = function(item) {
    var bibliography = this.getBibliography(item.parent());
    return bibliography[item.data.csl.id];
};

CitationGrid.prototype.getCitations = function(folder) {
    var self = this;
    return folder.children.filter(function(child) {
        return child.kind === 'file';
    }).map(function(child) {
        return self.getCitation(child);
    });
};

CitationGrid.prototype.resolveRowAux = function(item) {
    var self = this;
    return [
        {
            data: 'csl',
            folderIcons: true,
            custom: function(item) {
                return item.kind === 'folder' ? item.data.name : self.getCitation(item);
            }
        },
        {
            // Wrap callback in closure to preserve intended `this`
            custom: function() {
                return renderActions.apply(self, arguments);
            }
        }
    ];
};

module.exports = CitationGrid;
