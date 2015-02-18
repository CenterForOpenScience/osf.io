var $ = require('jquery');
var m = require('mithril');

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

    return m('.row', [
        m('.col-md-10.col-md-offset-1', [
            m('.row', [
                m('.col-md-12', ctrl.vm.results.map(ctrl.renderResult))
            ])
        ])
    ]);

};

Results.controller = function(vm) {
    var self = this;
    self.vm = vm;
    self.vm.resultsLoaded = false;

    self.renderResult = function(result) {
        return m('div', [
            m('div', [
                m('h4', [
                    m('a[href=' + result.id.url + ']', result.title),
                    m('br'),
                    (function(){
                        if (result.description.length > 250) {
                            return m('small.pointer',
                                {onclick:function(){result.showAll = result.showAll ? false : true;}},
                                result.showAll ? result.description : result.description.substring(0, 250) + '...'
                            );
                        }
                        return m('small', result.description);
                    }()),
                ]),
                m('br'),
                m('div', [
                    m('span', result.contributors.map(function(person) {
                        return person.given + ' ' + person.family;
                    }).join(' - ')),
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
