# -*- coding: utf-8 -*-
import re

re_spaces = re.compile(r"\s+", re.U)
re_word = re.compile(r"\w+", re.U)
re_mac = re.compile(r'^(ma?c)(\w+)', re.I | re.U)
re_initial = re.compile(r'^(\w\.|[A-Z])?$', re.U)

# do not include things that could also be first names, e.g. "dean"
# many of these from wikipedia: https://en.wikipedia.org/wiki/Title
# The parser recognizes chains of these including conjunctions allowing 
# recognition titles like "Deputy Secretary of State"
TITLES = set([
    'dr','doctor','miss','misses','mr','mister','mrs','ms','sir','dame',
    'rev','madam','madame','ab','2ndlt','amn','1stlt','a1c','capt','sra','maj',
    'ssgt','ltcol','tsgt','col','briggen','1stsgt','majgen','smsgt','ltgen',
    '1stsgt','cmsgt','1stsgt','ccmsgt','cmsaf','pvt','2lt','pv2','1lt',
    'pfc','cpt','spc','maj','cpl','ltc','sgt','ssg','bg','sfc','mg',
    'msg','ltg','1sgt','sgm','csm','sma','wo1','wo2','wo3','wo4','wo5',
    'ens','sa','ltjg','sn','lt','po3','lcdr','po2','cdr','po1','cpo',
    'radm(lh)','scpo','radm(uh)','mcpo','vadm','mcpoc','adm','mpco-cg',
    'pvt','2ndlt','pfc','1stlt','lcpl','cpl','sgt','ssgt','gysgt','bgen','msgt',
    'majgen','1stsgt','ltgen','mgysgt',
    'gen','sgtmaj','sgtmajmc','wo-1','cwo-2','cwo-3','cwo-4','cwo-5',
    'rdml','radm','mcpon','fadm','wo1','cwo2','cwo3','cwo4','cwo5',
    'rt','lord','lady','duke','dutchess','master','maid','uncle','auntie','aunt',
    'representative','senator','king','queen','cardinal','secretary','state',
    'foreign','minister','speaker','president','deputy','executive','vice',
    'councillor','alderman','delegate','mayor','lieutenant','governor','prefect',
    'prelate','premier','burgess','ambassador','envoy','secretary',u"attaché",
    u"chargé d'affaires",'provost',"marquis","marquess","marquise","marchioness",
    'archduke','archduchess','viscount','baron','emperor','empress','tsar',
    'tsarina','leader','abbess','abbot','brother','sister','friar','mother',
    'superior','reverend','bishop','archbishop','metropolitan','presbyter',
    'priest','high','priestess','father','patriarch','pope','catholicos',
    'vicar','chaplain','canon','pastor','prelate','primate','chaplain',
    'cardinal','servant','venerable','blessed','saint','member','solicitor',
    'mufti','grand','chancellor','barrister','bailiff','attorney','advocate',
    'deacon','archdeacon','acolyte','elder','minister','monsignor','almoner',
    'prof','colonel','general','commodore','air','corporal','staff','mate',
    'chief','first','sergeant','sergeant','admiral','high','rear','brigadier',
    'captain','group','commander','commander-in-chief','wing','general',
    'adjutant','director','generalissimo','resident','surgeon','officer',
    'academic','analytics','business','credit','financial','information',
    'security','knowledge','marketing','operating','petty','risk','security',
    'strategy','technical','warrant','corporate','customs','field','flag',
    'flying','intelligence','pilot','police','political','revenue','senior',
    'staff','private','principal','coach','nurse','nanny','docent','lama',
    'druid','archdruid','rabbi','rebbe','buddha','ayatollah','imam',
    'bodhisattva','mullah','mahdi','saoshyant','tirthankar','vardapet',
    'pharaoh','sultan','sultana','maharajah','maharani','elder',
    'vizier','chieftain','comptroller','courtier','curator','doyen','edohen',
    'ekegbian','elerunwon','forester','gentiluomo','headman','intendant',
    'lamido','marcher','matriarch','patriarch','prior','pursuivant','rangatira',
    'ranger','registrar','seigneur','sharif','shehu','sheikh','sheriff','subaltern',
    'subedar','sysselmann','timi','treasurer','verderer','warden','hereditary',
    'woodman','bearer','banner','swordbearer','apprentice','journeyman',
    'adept','akhoond','arhat','bwana','goodman','goodwife','bard','hajji','mullah',
    'baba','effendi','giani','gyani','guru','siddha','pir','murshid',
    'attache','prime','united','states','national','associate','assistant',
    'supreme','appellate','judicial',"queen's","king's",'bench','right','majesty',
    'his','her','kingdom','royal',
])

# PUNC_TITLES could be names or titles, but if they have period at the end they're a title
PUNC_TITLES = ('hon.',)

# words that prefix last names. Can be chained like "de la Vega"
# these should not be more common as first or middle names than prefixes
PREFIXES = set([
    'abu','bon','bin','da','dal','de','del','der','de','di',u'dí','ibn',
    'la','le','san','st','ste','van','vel','von'
])
SUFFIXES = set([
    'esq','esquire','jr','sr','2','i','ii','iii','iv','v','clu','chfc',
    'cfp','md','phd'
])
CAPITALIZATION_EXCEPTIONS = (
    ('ii' ,'II'),
    ('iii','III'),
    ('iv' ,'IV'),
    ('md' ,'M.D.'),
    ('phd','Ph.D.'),
)
CONJUNCTIONS = set(['&','and','et','e','of','the','und','y',])

# pre v0.2.5 support
PREFICES = PREFIXES 
SUFFICES = SUFFIXES
