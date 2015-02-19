var $ = require('jquery');
var m = require('mithril');
var $osf = require('osfHelpers');

var ProviderMap = {
    arxiv_oai: {name: 'ArXiv', link: 'http://arxiv.org'},
    calpoly: {name: 'Digital Commons at Cal Poly', link: 'http://digitalcommons.calpoly.edu/'},
    cmu: {name: 'Carnegie Mellon University Research Showcase', link: 'http://repository.cmu.edu/'},
    clinicaltrials: {name: 'ClinicalTrials.gov', link: 'https://clinicaltrials.gov/'},
    crossref: {name: 'CrossRef', link: 'http://www.crossref.org/'},
    doepages: {name: 'Department of Energy Pages', link: 'http://www.osti.gov/pages/'},
    columbia: {name: 'Columbia Adacemic Commons', link: 'http://academiccommons.columbia.edu/'},
    dataone: {name: 'DataONE: Data Observation Network for Earth', link: 'https://www.dataone.org/'},
    figshare: {name: 'figshare', link: 'http://figshare.com/account/my_data'},
    mit: {name: 'DSpace@MIT', link: 'http://dspace.mit.edu/'},
    opensiuc: {name: 'OpenSIUC at the Southern Illinois University Carbondale', link: 'http://opensiuc.lib.siu.edu/'},
    plos: {name: 'Public Library Of Science', link: 'http://www.plos.org/'},
    pubmed: {name: 'PubMed Central', link: 'http://www.ncbi.nlm.nih.gov/pmc/'},
    spdataverse: {name: 'Scholars Portal Dataverse', link: 'http://dataverse.scholarsportal.info/dvn/'},
    scitech: {name: 'SciTech Connect', link: 'http://www.osti.gov/scitech/'},
    stcloud: {name: 'theRepository at St. Cloud State'},
    texasstate: {name: 'DSpace at Texas State University', link: 'https://digital.library.txstate.edu/'},
    trinity: {name: 'Digital Commons@Trinity', link: 'http://digitalcommons.trinity.edu/'},
    ucescholership: {name: 'California Digital Library eScholarship System', link: 'http://www.escholarship.org/'},
    uiucideals: {name: 'University of Illinois at Urbana-Champaign Illinois Digital Enviornment for Access to Learning and Scholarship', link: 'https://www.ideals.illinois.edu/'},
    upennsylvania: {name: 'University of Pennsylvania Scholarly Commons', link: 'http://repository.upenn.edu/'},
    utaustin: {name: 'University of Texas Digital Repository', link: 'https://repositories.lib.utexas.edu/'},
    uwdspace: {name: 'ResearchWorks at the University of Washington', link: 'https://digital.lib.washington.edu/'},
    valposcholar: {name: 'Valparaiso University ValpoScholar', link: 'http://scholar.valpo.edu/'},
    vtech: {name: 'Virginia Tech VTechWorks', link: 'https://vtechworks.lib.vt.edu/'},
    waynestate: {name: 'DigitalCommons@WayneState', link: 'http://digitalcommons.wayne.edu/'},
};

var Results = {};

Results.view = function(ctrl) {
    if (!ctrl.vm.resultsLoaded) {
        return m('img[src=/static/img/spinner.gif');
    }

    return m('.row', m('.col-md-12', ctrl.vm.results.map(ctrl.renderResult)));

};

Results.controller = function(vm) {
    var self = this;
    self.vm = vm;
    self.vm.resultsLoaded = false;

    self.renderResult = function(result, index) {
        return m( '.animated.fadeInUp', [
            m('div', [
                m('h4', [
                    m('a[href=' + result.id.url + ']', result.title),
                    m('br'),
                    (function(){
                        if (result.description.length > 350) {
                            return m('small.pointer',
                                {onclick:function(){result.showAll = result.showAll ? false : true;}},
                                result.showAll ? result.description : result.description.substring(0, 350).trimRight() + '...'
                            );
                        }
                        return m('small', result.description);
                    }()),
                ]),
                m('.row', [
                    m('.col-md-7', m('span.pull-left', (function(){
                        var renderPeople = function(people) {
                            return m('span', people.map(function(person) {
                                return person.given + ' ' + person.family;
                            }).join(' - '));
                        };

                        return m('span.pull-left', {style: {'text-align': 'center'}, class: result.contributors.length > 8 ? 'pointer' : '',
                            onclick:function(){result.showAllContrib = result.showAllContrib ? false : true;}},
                            result.showAllContrib || result.contributors.length < 8 ?
                                renderPeople(result.contributors) :
                                m('span', [
                                    renderPeople(result.contributors.slice(0, 7)),
                                    m('br'),
                                    m('a', 'See All')
                                ])
                        );
                    }()))),
                    m('.col-md-5',
                        m('.pull-right', {style: {'text-align': 'center'}, class: result.tags.length > 5 ? 'pointer' : '',
                          onclick: function() {result.showAllTags = result.showAllTags ? false : true;}},
                          result.showAllTags || result.tags.length < 5 ?
                            result.tags.map(function(tag) {return m('.badge', tag);}) :
                            m('span', [
                                result.tags.slice(0, 5).map(function(tag){return m('.badge', tag);}),
                                m('br'),
                                m('div', m('a', 'See All'))
                            ])
                         )
                     )
                ]),
                m('br'),
                m('br'),
                m('div', [
                    m('span', 'Released on ' + new $osf.FormattableDate(result.dateUpdated).local),
                    m('span.pull-right', [
                        m('img', {src: '/static/img/share/' + result.source + '_favicon.ico'}),
                        ' ',
                        m('a', {href: ProviderMap[result.source].link}, ProviderMap[result.source].name)
                    ])
                ])
            ]),
            m('hr')
        ]);
    };


    self.loadMore = function() {
        self.vm.page++;
        var page = (self.vm.page + 1) * 10;

        m.request({
            method: 'get',
            url: '/api/v1/share/?from=' + page + '&q=' + self.vm.query(),
        }).then(function(data) {
            self.vm.time = data.time;
            self.vm.count = data.count;

            // push.apply is the same as extend in python
            self.vm.results.push.apply(self.vm.results, data.results);

            self.vm.resultsLoaded = true;
        });
    };

    $(window).scroll(function() {
        if  ($(window).scrollTop() === $(document).height() - $(window).height()){
            self.loadMore();
        }
    });

    self.loadMore();
};

module.exports = Results;
