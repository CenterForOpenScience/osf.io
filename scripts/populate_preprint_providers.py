#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Preprint Provider elements"""

import logging
import sys

from django.db import transaction
from website.app import init_app
from website.settings import PREPRINT_PROVIDER_DOMAINS, DOMAIN, PROTOCOL
import django
django.setup()

from osf.models import Subject, PreprintProvider, NodeLicense, NotificationSubscription

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ENVS = ['prod', 'stage']
SUBJECTS_CACHE = {}
STAGING_PREPRINT_PROVIDERS = ['osf', 'psyarxiv', 'engrxiv', 'socarxiv', 'scielo', 'agrixiv', 'bitss', 'lawarxiv']
PROD_PREPRINT_PROVIDERS = ['osf', 'psyarxiv', 'engrxiv', 'socarxiv', 'agrixiv', 'bitss', 'lawarxiv']


def get_subject_id(name):
    if name not in SUBJECTS_CACHE:
        subject = None
        try:
            subject = Subject.objects.get(provider___id='osf', text=name)
        except Subject.DoesNotExist:
            raise Exception('Subject: "{}" not found'.format(name))
        else:
            SUBJECTS_CACHE[name] = subject._id

    return SUBJECTS_CACHE[name]


def get_license(name):
    try:
        license = NodeLicense.objects.get(name=name)
    except NodeLicense.DoesNotExist:
        raise Exception('License: "{}" not found'.format(name))
    return license


def update_or_create(provider_data):
    provider = PreprintProvider.load(provider_data['_id'])
    provider_data['domain_redirect_enabled'] &= PREPRINT_PROVIDER_DOMAINS['enabled'] and bool(provider_data['domain'])
    licenses = [get_license(name) for name in provider_data.pop('licenses_acceptable', [])]
    default_license = provider_data.pop('default_license', False)

    if provider:
        provider_data['subjects_acceptable'] = map(
            lambda rule: (map(get_subject_id, rule[0]), rule[1]),
            provider_data['subjects_acceptable']
        )
        if licenses:
            provider.licenses_acceptable.add(*licenses)
        if default_license:
            provider.default_license = get_license(default_license)
        for key, val in provider_data.iteritems():
            setattr(provider, key, val)
        changed_fields = provider.save()
        if changed_fields:
            print('Updated {}: {}'.format(provider.name, changed_fields))
        return provider, False
    else:
        new_provider = PreprintProvider(**provider_data)
        new_provider.save()
        if licenses:
            new_provider.licenses_acceptable.add(*licenses)
        if default_license:
            new_provider.default_license = get_license(default_license)
            new_provider.save()
        provider = PreprintProvider.load(new_provider._id)
        print('Added new preprint provider: {}'.format(provider._id))
        return new_provider, True


def format_domain_url(domain):
    prefix = PREPRINT_PROVIDER_DOMAINS['prefix'] or PROTOCOL
    suffix = PREPRINT_PROVIDER_DOMAINS['suffix'] or '/'

    return '{}{}{}'.format(prefix, str(domain), suffix)


def main(env):
    PREPRINT_PROVIDERS = {
        'osf': {
            '_id': 'osf',
            'name': 'Open Science Framework',
            'share_publish_type': 'Preprint',
            'description': 'A scholarly commons to connect the entire research cycle',
            'domain': DOMAIN,
            'domain_redirect_enabled': False,  # Never change this
            'external_url': 'https://osf.io/preprints/',
            'example': 'khbvy',
            'advisory_board': '',
            'email_contact': '',
            'email_support': '',
            'social_twitter': '',
            'social_facebook': '',
            'social_instagram': '',
            'default_license': 'CC0 1.0 Universal',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'subjects_acceptable': [],
        },
        'engrxiv': {
            '_id': 'engrxiv',
            'name': 'engrXiv',
            'share_publish_type': 'Preprint',
            'description': 'The open archive of engineering.',
            'domain': format_domain_url('engrxiv.org'),
            'domain_redirect_enabled': False,
            'external_url': 'http://engrxiv.com',
            'example': 'k7fgk',
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Steering Committee</h2>
                    <p class="m-b-lg">engrXiv is directed by a steering committee of engineers and members of the engineering librarian community. They are:</p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><a href="http://libguides.mit.edu/profiles/psayers">Phoebe Ayers</a>, librarian, Massachusetts Institute of Technology</li>
                        <li><a href="http://stem.gwu.edu/lorena-barba">Lorena A. Barba</a>, aerospace engineer, The George Washington University</li>
                        <li><a href="http://www.devinberg.com/">Devin R. Berg</a>, mechanical engineer, University of Wisconsin-Stout</li>
                        <li><a href="http://mime.oregonstate.edu/people/dupont">Bryony Dupont</a>, mechanical engineer, Oregon State University</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><a href="http://directory.uark.edu/people/dcjensen">David Jensen</a>, mechanical engineer, University of Arkansas</li>
                        <li><a href="http://biomech.media.mit.edu/people/">Kevin Moerman</a>, biomechanical engineer, Massachusetts Institute of Technology</li>
                        <li><a href="http://kyleniemeyer.com/">Kyle Niemeyer</a>, mechanical engineer, Oregon State University</li>
                        <li><a href="http://www.douglasvanbossuyt.com/">Douglas Van Bossuyt</a>, mechanical engineer, KTM Research</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+engrxiv@osf.io',
            'email_support': 'support+engrxiv@osf.io',
            'social_twitter': 'engrxiv',
            'social_facebook': 'engrXiv',
            'social_instagram': 'engrxiv',
            'default_license': 'CC0 1.0 Universal',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'subjects_acceptable': [
                (['Architecture', 'Architectural Engineering'], True),
                (['Engineering', 'Aerospace Engineering', 'Aerodynamics and Fluid Mechanics'], False),
                (['Engineering', 'Aerospace Engineering', 'Aeronautical Vehicles'], False),
                (['Engineering', 'Aerospace Engineering', 'Astrodynamics'], False),
                (['Engineering', 'Aerospace Engineering', 'Multi-Vehicle Systems and Air Traffic Control'], False),
                (['Engineering', 'Aerospace Engineering', 'Navigation, Guidance, Control and Dynamics'], False),
                (['Engineering', 'Aerospace Engineering', 'Propulsion and Power'], False),
                (['Engineering', 'Aerospace Engineering', 'Space Vehicles'], False),
                (['Engineering', 'Aerospace Engineering', 'Structures and Materials'], False),
                (['Engineering', 'Aerospace Engineering', 'Systems Engineering and Multidisciplinary Design Optimization'], False),
                (['Engineering', 'Aerospace Engineering', 'Other Aerospace Engineering'], False),
                (['Engineering', 'Automotive Engineering'], True),
                (['Engineering', 'Aviation', 'Aviation Safety and Security'], False),
                (['Engineering', 'Aviation', 'Maintenance Technology'], False),
                (['Engineering', 'Aviation', 'Management and Operations'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Bioelectrical and Neuroengineering'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Bioimaging and Biomedical Optics'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Biological Engineering'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Biomaterials'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Biomechanics and Biotransport'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Biomedical Devices and Instrumentation'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Molecular, Cellular, and Tissue Engineering'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Systems and Integrative Engineering'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Vision Science'], False),
                (['Engineering', 'Biomedical Engineering and Bioengineering', 'Other Biomedical Engineering and Bioengineering'], False),
                (['Engineering', 'Bioresource and Agricultural Engineering'], True),
                (['Engineering', 'Chemical Engineering', 'Biochemical and Biomolecular Engineering'], False),
                (['Engineering', 'Chemical Engineering', 'Catalysis and Reaction Engineering'], False),
                (['Engineering', 'Chemical Engineering', 'Complex Fluids'], False),
                (['Engineering', 'Chemical Engineering', 'Membrane Science'], False),
                (['Engineering', 'Chemical Engineering', 'Petroleum Engineering'], False),
                (['Engineering', 'Chemical Engineering', 'Polymer Science'], False),
                (['Engineering', 'Chemical Engineering', 'Process Control and Systems'], False),
                (['Engineering', 'Chemical Engineering', 'Thermodynamics'], False),
                (['Engineering', 'Chemical Engineering', 'Transport Phenomena'], False),
                (['Engineering', 'Chemical Engineering', 'Other Chemical Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Civil Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Construction Engineering and Management'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Environmental Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Geotechnical Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Hydraulic Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Structural Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Transportation Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering', 'Other Civil and Environmental Engineering'], False),
                (['Engineering', 'Computational Engineering'], True),
                (['Engineering', 'Computer Engineering', 'Computer and Systems Architecture'], False),
                (['Engineering', 'Computer Engineering', 'Data Storage Systems'], False),
                (['Engineering', 'Computer Engineering', 'Digital Circuits'], False),
                (['Engineering', 'Computer Engineering', 'Digital Communications and Networking'], False),
                (['Engineering', 'Computer Engineering', 'Hardware Systems'], False),
                (['Engineering', 'Computer Engineering', 'Robotics'], False),
                (['Engineering', 'Computer Engineering', 'Other Computer Engineering'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Biomedical'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Controls and Control Theory'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Electrical and Electronics'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Electromagnetics and Photonics'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Electronic Devices and Semiconductor Manufacturing'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Nanotechnology Fabrication'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Power and Energy'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Signal Processing'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Systems and Communications'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'VLSI and Circuits, Embedded and Hardware Systems'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Other Electrical and Computer Engineering'], False),
                (['Engineering', 'Engineering Education'], True),
                (['Engineering', 'Engineering Science and Materials', 'Dynamics and Dynamical Systems'], False),
                (['Engineering', 'Engineering Science and Materials', 'Engineering Mechanics'], False),
                (['Engineering', 'Engineering Science and Materials', 'Mechanics of Materials'], False),
                (['Engineering', 'Engineering Science and Materials', 'Other Engineering Science and Materials'], False),
                (['Engineering', 'Materials Science and Engineering', 'Biology and Biomimetic Materials'], False),
                (['Engineering', 'Materials Science and Engineering', 'Ceramic Materials'], False),
                (['Engineering', 'Materials Science and Engineering', 'Metallurgy'], False),
                (['Engineering', 'Materials Science and Engineering', 'Polymer and Organic Materials'], False),
                (['Engineering', 'Materials Science and Engineering', 'Semiconductor and Optical Materials'], False),
                (['Engineering', 'Materials Science and Engineering', 'Structural Materials'], False),
                (['Engineering', 'Materials Science and Engineering', 'Other Materials Science and Engineering'], False),
                (['Engineering', 'Mechanical Engineering', 'Acoustics, Dynamics, and Controls'], False),
                (['Engineering', 'Mechanical Engineering', 'Applied Mechanics'], False),
                (['Engineering', 'Mechanical Engineering', 'Biomechanical Engineering'], False),
                (['Engineering', 'Mechanical Engineering', 'Computer-Aided Engineering and Design'], False),
                (['Engineering', 'Mechanical Engineering', 'Electro-Mechanical Systems'], False),
                (['Engineering', 'Mechanical Engineering', 'Energy Systems'], False),
                (['Engineering', 'Mechanical Engineering', 'Heat Transfer, Combustion'], False),
                (['Engineering', 'Mechanical Engineering', 'Manufacturing'], False),
                (['Engineering', 'Mechanical Engineering', 'Ocean Engineering'], False),
                (['Engineering', 'Mechanical Engineering', 'Tribology'], False),
                (['Engineering', 'Mechanical Engineering', 'Other Mechanical Engineering'], False),
                (['Engineering', 'Mining Engineering'], True),
                (['Engineering', 'Nanoscience and Nanotechnology'], True),
                (['Engineering', 'Nuclear Engineering'], True),
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering', 'Ergonomics'], False),
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering', 'Industrial Engineering'], False),
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering', 'Industrial Technology'], False),
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering', 'Operational Research'], False),
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering', 'Systems Engineering'], False),
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering', 'Other Operations Research, Systems Engineering and Industrial Engineering'], False),
                (['Engineering', 'Risk Analysis'], True),
                (['Engineering', 'Other Engineering'], True),
                (['Physical Sciences and Mathematics', 'Physics', 'Engineering Physics'], False),
            ],
        },
        'psyarxiv': {
            '_id': 'psyarxiv',
            'name': 'PsyArXiv',
            'share_publish_type': 'Preprint',
            'description': 'A free preprint service for the psychological sciences.',
            'domain': format_domain_url('psyarxiv.com'),
            'domain_redirect_enabled': False,
            'external_url': 'http://psyarxiv.org',
            'example': 'k9mn3',
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Steering Committee</h2>
                    <p class="m-b-lg"></p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Jack Arnal</b>, McDaniel College</li>
                        <li><b>David Barner</b>, University of California, San Diego</li>
                        <li><b>Benjamin Brown</b>, Georgia Gwinnett College</li>
                        <li><b>David Condon</b>, Northwestern University</li>
                        <li><b>Will Cross</b>, North Carolina State University Libraries</li>
                        <li><b>Anita Eerland</b>, Utrecht University</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Chris Hartgerink</b>, Tilburg University</li>
                        <li><b>Alex Holcombe</b>, University of Sydney</li>
                        <li><b>Jeff Hughes</b>, University of Waterloo</li>
                        <li><b>Don Moore</b>, University of California, Berkeley</li>
                        <li><b>Sean Rife</b>, Murray State University</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+psyarxiv@osf.io',
            'email_support': 'support+psyarxiv@osf.io',
            'social_twitter': 'psyarxiv',
            'social_facebook': 'PsyArXiv',
            'social_instagram': 'psyarxiv',
            'default_license': 'CC0 1.0 Universal',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'subjects_acceptable': [
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering', 'Ergonomics'], False),
                (['Life Sciences', 'Neuroscience and Neurobiology', 'Behavioral Neurobiology'], False),
                (['Life Sciences', 'Neuroscience and Neurobiology', 'Cognitive Neuroscience'], False),
                (['Life Sciences', 'Neuroscience and Neurobiology', 'Computational Neuroscience'], False),
                (['Life Sciences', 'Neuroscience and Neurobiology', 'Developmental Neuroscience'], False),
                (['Life Sciences', 'Neuroscience and Neurobiology', 'Molecular and Cellular Neuroscience'], False),
                (['Life Sciences', 'Neuroscience and Neurobiology', 'Systems Neuroscience'], False),
                (['Life Sciences', 'Neuroscience and Neurobiology', 'Other Neuroscience and Neurobiology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Applied Behavior Analysis'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Biological Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Child Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Clinical Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Cognition and Perception'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Cognitive Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Community Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Counseling Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Developmental Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Experimental Analysis of Behavior'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Health Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Industrial and Organizational Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Multicultural Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Pain Management'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Personality and Social Contexts'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Quantitative Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'School Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Social Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Theory and Philosophy'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Other Psychology'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Anthropological Linguistics and Sociolinguistics'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Applied Linguistics'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Comparative and Historical Linguistics'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Computational Linguistics'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Discourse and Text Linguistics'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'First and Second Language Acquisition'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Language Description and Documentation'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Morphology'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Phonetics and Phonology'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Psycholinguistics and Neurolinguistics'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Semantics and Pragmatics'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Syntax'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Typological Linguistics and Linguistic Diversity'], False),
                (['Social and Behavioral Sciences', 'Linguistics', 'Other Linguistics'], False),
            ],
        },
        'socarxiv': {
            '_id': 'socarxiv',
            'name': 'SocArXiv',
            'share_publish_type': 'Preprint',
            'description': 'Open archive of the social sciences',
            'domain': format_domain_url('socarxiv.org'),
            'domain_redirect_enabled': False,
            'external_url': 'http://socarxiv.org',
            'example': 'qmdc4',
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Steering Committee</h2>
                    <p class="m-b-lg"></p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Elizabeth Popp Berman</b>, University at Albany SUNY</li>
                        <li><b>Chris Bourg</b>, Massachusetts Institute of Technology</li>
                        <li><b>Neal Caren</b>, University of North Carolina at Chapel Hill</li>
                        <li><b>Philip N. Cohen</b>, University of Maryland, College Park</li>
                        <li><b>Tressie McMillan Cottom</b>, Virginia Commonwealth University</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Tina Fetner</b>, McMaster University</li>
                        <li><b>Dan Hirschman</b>, Brown University</li>
                        <li><b>Rebecca Kennison</b>, K|N Consultants</li>
                        <li><b>Judy Ruttenberg</b>, Association of Research Libraries</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+socarxiv@osf.io',
            'email_support': 'support+socarxiv@osf.io',
            'social_twitter': 'socarxiv',
            'social_facebook': 'socarxiv',
            'social_instagram': 'socarxiv',
            'default_license': 'CC0 1.0 Universal',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'subjects_acceptable': [
                (['Arts and Humanities'], True),
                (['Education'], True),
                (['Law'], True),
                (['Social and Behavioral Sciences'], True),
            ],
        },
        'scielo': {
            '_id': 'scielo',
            'name': 'SciELO',
            'share_publish_type': 'Preprint',
            'description': 'Advancing Research Communication',
            'domain': format_domain_url('scielo.org'),
            'domain_redirect_enabled': False,
            'external_url': 'http://scielo.org',
            'example': '',  # An example guid for this provider (Will have to be updated after the provider is up)
            # Advisory board should be valid html string in triple quotes
            'advisory_board': '',
            'email_contact': 'contact+scielo@osf.io',
            'email_support': 'support+scielo@osf.io',
            'social_twitter': 'RedeSciELO',  # optional
            'social_facebook': 'SciELONetwork',
            'default_license': 'CC-By Attribution 4.0 International',
            'licenses_acceptable': ['CC-By Attribution 4.0 International'],
            'subjects_acceptable': []
        },
        'lawarxiv': {
            '_id': 'lawarxiv',
            'name': 'LawArXiv',
            'share_publish_type': 'Preprint',
            'description': 'Legal Scholarship in the Open',
            'domain': '',  # No domain information yet
            'domain_redirect_enabled': False,
            'external_url': '',
            'example': 'vk7yp',  # An example guid for this provider (Will have to be updated after the provider is up)
            # Advisory board should be valid html string in triple quotes
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Legal Scholarship Advisory Board</h2>
                    <p class="m-b-lg"></p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li> <b>Timothy Armstrong</b>, University of Cincinnati College of Law</li>
                        <li> <b>Barbara Bintliff</b>, Texas Law </li>
                        <li> <b>Femi Cadmus</b>, Cornell Law School </li>
                        <li> <b>Kyle Courtney</b>, Harvard University </li>
                        <li> <b>Corie Dugas</b>, Mid-America Law Library Consortium </li>
                        <li> <b>James Grimmelmann</b>, Cornell Tech and Cornell Law School </li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li> <b>Lydia Loren</b>, Lewis & Clark Law School </li>
                        <li> <b>Margaret Maes</b>, Legal Information Preservation Alliance </li>
                        <li> <b>Susan Nevelow Mart</b>, University of Colorado Law School </li>
                        <li> <b>Roger Skalbeck</b>, University of Richmond School of Law </li>
                        <li> <b>Tracy Thompson</b>, NELLCO Law Library Consortium </li>
                        <li> <b>Siva Vaidhyanathan</b>, University of Virginia Department of Media Studies </li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+lawarxiv@osf.io',
            'email_support': 'support+lawarxiv@osf.io',
            'social_twitter': 'lawarxiv',
            'social_facebook': '',
            'default_license': 'No license',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'subjects_acceptable': [
                (['Arts and Humanities'], True),
                (['Business'], True),
                (['Education'], True),
                (['Law'], True),
                (['Medicine and Health Sciences'], True),
                (['Social and Behavioral Sciences'], True),
            ]
        },
        'agrixiv': {
            '_id': 'agrixiv',
            'name': 'AgriXiv',
            'share_publish_type': 'Preprint',
            'description': 'Preprints for Agriculture and Allied Sciences',
            'domain': format_domain_url('agrixiv.org'),
            'domain_redirect_enabled': False,
            'external_url': '',
            'example': '8whkp',
            'advisory_board': '''
                <div class="col-xs-6">
                    <h3>Advisory Board</h3>
                    <p class="m-b-lg"></p>
                </div>
                <div class="col-xs-6">
                    <h3>Working Group</h3>
                    <p class="m-b-lg"></p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Abeer Elhalwagi</b>, National Gene Bank, Egypt</li>
                        <li><b>Ajit Maru</b>, Global Forum on Agricultural Research</li>
                        <li><b>Bernard Pochet</b>, University of Liège - Gembloux Agro-Bio Tech</li>
                        <li><b>Dinesh Kumar</b>, Indian Agricultural Statistics Research Institute</li>
                        <li><b>Oya Yildirim Rieger</b>, Cornell University</li>
                        <li><b>Prateek Mahalwar</b>, Ernst & Young GmbH Wirtschaftsprüfungsgesellschaft</li>
                        <li><b>Satendra Kumar Singh</b>, Indian Council of Agricultural Research</li>
                        <li><b>Vassilis Protonotarios</b>, Neuropublic</li>
                        <li><b>Vinodh Ilangovan</b>, Max Planck Institute for Biophysical Chemistry</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Chandni Singh</b>, Indian Institute for Human Settlements</li>
                        <li><b>Gopinath KA</b>, Central Research Institute for Dryland Agriculture</li>
                        <li><b>Ivonne Lujano</b>, University of the State of Mexico</li>
                        <li><b>Khelif Karima</b>, Institut National de la Recherche Agronomique d'Algérie</li>
                        <li><b>Kuldeep Singh Jadon</b>, Central Arid Zone Research Institute</li>
                        <li><b>Paraj Shukla</b>, King Saud University</li>
                        <li><b>Sridhar Gutam</b>,  ICAR RCER Research Centre/Open Access India</li>
                        <li><b>Sumant Vyas</b>, National Research Centre on Camel</li>
                        <li><b>Susmita Das</b>, Bangladesh Agricultural Research Council</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+agrixiv@osf.io',
            'email_support': 'support+agrixiv@osf.io',
            'social_twitter': 'AgriXiv',
            'social_facebook': 'agrixiv',
            'social_instagram': 'agrixiv',
            'default_license': 'CC0 1.0 Universal',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International'],
            'subjects_acceptable': [
                (['Business', 'Business Administration, Management, and Operations'], False),
                (['Business', 'Business and Corporate Communications'], False),
                (['Business', 'Business Intelligence'], False),
                (['Business', 'Business Law, Public Responsibility, and Ethics Business'], False),
                (['Business', 'Corporate Finance'], False),
                (['Business', 'E-Commerce'], False),
                (['Business', 'Entrepreneurial and Small Business Operations'], False),
                (['Business', 'Fashion Business'], False),
                (['Business', 'Finance and Financial Management'], False),
                (['Business', 'Human Resources Management'], False),
                (['Business', 'Agribusiness', 'Benefits and Compensation'], False),
                (['Business', 'Agribusiness', 'Performance Management'], False),
                (['Business', 'Agribusiness', 'Training and Development'], False),
                (['Business', 'Management Information Systems'], False),
                (['Business', 'Management Sciences and Quantitative Methods'], False),
                (['Business', 'Marketing'], False),
                (['Business', 'Nonprofit Administration and Management'], False),
                (['Business', 'Operations and Supply Chain Management'], False),
                (['Business', 'Organizational Behavior and Theory'], False),
                (['Business', 'Portfolio and Security Analysis'], False),
                (['Business', 'Other Business'], False),
                (['Education', 'Curriculum and Instruction'], False),
                (['Education', 'Curriculum and Social Inquiry'], False),
                (['Education', 'Education Economics'], False),
                (['Education', 'Educational Administration and Supervision'], False),
                (['Education', 'Insurance', 'Adult and Continuing Education Administration'], False),
                (['Education', 'Insurance', 'Other Educational Administration and Supervision'], False),
                (['Education', 'Educational Leadership'], False),
                (['Education', 'Educational Methods'], False),
                (['Education', 'Educational Psychology'], False),
                (['Education', 'Higher Education'], False),
                (['Education', 'Educational Assessment, Evaluation, and Research', 'Scholarship of Teaching and Learning'], False),
                (['Education', 'Educational Assessment, Evaluation, and Research', 'University Extension'], False),
                (['Education', 'Humane Education'], False),
                (['Education', 'Instructional Media Design'], False),
                (['Education', 'International and Comparative Education'], False),
                (['Education', 'Online and Distance Education'], False),
                (['Education', 'Science and Mathematics Education'], False),
                (['Education', 'Social and Philosophical Foundations of Education'], False),
                (['Education', 'Special Education and Teaching'], False),
                (['Education', 'Student Counseling and Personnel Services'], False),
                (['Education', 'Other Education'], False),
                (['Engineering', 'Bioresource and Agricultural Engineering'], False),
                (['Engineering', 'Civil and Environmental Engineering'], False),
                (['Engineering', 'Home Economics', 'Environmental Engineering'], False),
                (['Engineering', 'Home Economics', 'Structural Engineering'], False),
                (['Engineering', 'Home Economics', 'Other Civil and Environmental Engineering'], False),
                (['Engineering', 'Computer Engineering'], False),
                (['Engineering', 'Computational Engineering', 'Computer and Systems Architecture'], False),
                (['Engineering', 'Computational Engineering', 'Data Storage Systems'], False),
                (['Engineering', 'Computational Engineering', 'Digital Circuits'], False),
                (['Engineering', 'Computational Engineering', 'Digital Communications and Networking'], False),
                (['Engineering', 'Computational Engineering', 'Hardware Systems'], False),
                (['Engineering', 'Computational Engineering', 'Robotics'], False),
                (['Engineering', 'Computational Engineering', 'Other Computer Engineering'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Nanotechnology Fabrication'], False),
                (['Engineering', 'Electrical and Computer Engineering', 'Power and Energy'], False),
                (['Engineering', 'Operations Research, Systems Engineering and Industrial Engineering'], False),
                (['Engineering', 'Nanoscience and Nanotechnology', 'Ergonomics'], False),
                (['Engineering', 'Nanoscience and Nanotechnology', 'Systems Engineering'], False),
                (['Engineering', 'Nanoscience and Nanotechnology', 'Other Operations Research, Systems Engineering and Industrial Engineering'], False),
                (['Engineering', 'Other Engineering'], False),
                (['Law', 'Agriculture Law'], False),
                (['Law', 'Animal Law'], False),
                (['Law', 'Antitrust and Trade Regulation'], False),
                (['Law', 'Banking and Finance Law'], False),
                (['Law', 'Business Organizations Law'], False),
                (['Law', 'Communications Law'], False),
                (['Law', 'Consumer Protection Law'], False),
                (['Law', 'Contracts'], False),
                (['Law', 'Dispute Resolution and Arbitration'], False),
                (['Law', 'Education Law'], False),
                (['Law', 'Environmental Law'], False),
                (['Law', 'Human Rights Law'], False),
                (['Law', 'Insurance Law'], False),
                (['Law', 'Intellectual Property Law'], False),
                (['Law', 'International Law'], False),
                (['Law', 'International Trade Law'], False),
                (['Law', 'Internet Law'], False),
                (['Law', 'Labor and Employment Law'], False),
                (['Law', 'Land Use Law'], False),
                (['Law', 'Law and Economics'], False),
                (['Law', 'Law and Gender'], False),
                (['Law', 'Law Enforcement and Corrections'], False),
                (['Law', 'Law of the Sea'], False),
                (['Law', 'Legal Education'], False),
                (['Law', 'Legal Ethics and Professional Responsibility'], False),
                (['Law', 'Legal Writing and Research'], False),
                (['Law', 'Legislation'], False),
                (['Law', 'Litigation'], False),
                (['Law', 'Marketing Law'], False),
                (['Law', 'Natural Resources Law'], False),
                (['Law', 'Science and Technology Law'], False),
                (['Law', 'Second Amendment'], False),
                (['Law', 'Water Law'], False),
                (['Law', 'Other Law'], False),
                (['Life Sciences', 'Agriculture'], False),
                (['Life Sciences', 'Risk Analysis', 'Agricultural Economics'], False),
                (['Life Sciences', 'Risk Analysis', 'Agricultural Education'], False),
                (['Life Sciences', 'Risk Analysis', 'Apiculture'], False),
                (['Life Sciences', 'Risk Analysis', 'Biosecurity'], False),
                (['Life Sciences', 'Risk Analysis', 'Viticulture and Oenology'], False),
                (['Life Sciences', 'Animal Sciences', 'Aquaculture and Fisheries Life Sciences'], False),
                (['Life Sciences', 'Animal Sciences', 'Dairy Science'], False),
                (['Life Sciences', 'Animal Sciences', 'Meat Science'], False),
                (['Life Sciences', 'Animal Sciences', 'Ornithology'], False),
                (['Life Sciences', 'Animal Sciences', 'Poultry or Avian Science'], False),
                (['Life Sciences', 'Animal Sciences', 'Sheep and Goat Science'], False),
                (['Life Sciences', 'Animal Sciences', 'Zoology'], False),
                (['Life Sciences', 'Animal Sciences', 'Other Animal Sciences'], False),
                (['Life Sciences', 'Biochemistry, Biophysics, and Structural Biology', 'Biochemistry'], False),
                (['Life Sciences', 'Biochemistry, Biophysics, and Structural Biology', 'Biophysics'], False),
                (['Life Sciences', 'Biochemistry, Biophysics, and Structural Biology', 'Molecular Biology'], False),
                (['Life Sciences', 'Biochemistry, Biophysics, and Structural Biology', 'Structural Biology'], False),
                (['Life Sciences', 'Biochemistry, Biophysics, and Structural Biology', 'Other Biochemistry, Biophysics, and Structural Biology'], False),
                (['Life Sciences', 'Bioinformatics'], False),
                (['Life Sciences', 'Biology'], False),
                (['Life Sciences', 'Biodiversity', 'Integrative Biology'], False),
                (['Life Sciences', 'Cell and Developmental Biology'], False),
                (['Life Sciences', 'Biotechnology', 'Cancer Biology'], False),
                (['Life Sciences', 'Biotechnology', 'Cell Anatomy'], False),
                (['Life Sciences', 'Biotechnology', 'Cell Biology'], False),
                (['Life Sciences', 'Biotechnology', 'Developmental Biology'], False),
                (['Life Sciences', 'Biotechnology', 'Other Cell and Developmental Biology'], False),
                (['Life Sciences', 'Ecology and Evolutionary Biology', 'Behavior and Ethology'], False),
                (['Life Sciences', 'Ecology and Evolutionary Biology', 'Desert Ecology'], False),
                (['Life Sciences', 'Ecology and Evolutionary Biology', 'Evolution'], False),
                (['Life Sciences', 'Ecology and Evolutionary Biology', 'Population Biology'], False),
                (['Life Sciences', 'Ecology and Evolutionary Biology', 'Terrestrial and Aquatic Ecology'], False),
                (['Life Sciences', 'Ecology and Evolutionary Biology', 'Other Ecology and Evolutionary Biology'], False),
                (['Life Sciences', 'Food Science'], False),
                (['Life Sciences', 'Entomology', 'Food Biotechnology'], False),
                (['Life Sciences', 'Entomology', 'Food Chemistry'], False),
                (['Life Sciences', 'Entomology', 'Food Microbiology'], False),
                (['Life Sciences', 'Entomology', 'Food Processing'], False),
                (['Life Sciences', 'Entomology', 'Other Food Science'], False),
                (['Life Sciences', 'Forest Sciences', 'Forest Biology'], False),
                (['Life Sciences', 'Forest Sciences', 'Forest Management'], False),
                (['Life Sciences', 'Forest Sciences', 'Wood Science and Pulp, Paper Technology'], False),
                (['Life Sciences', 'Forest Sciences', 'Other Forestry and Forest Sciences'], False),
                (['Life Sciences', 'Genetics and Genomics', 'Computational Biology'], False),
                (['Life Sciences', 'Genetics and Genomics', 'Genetics'], False),
                (['Life Sciences', 'Genetics and Genomics', 'Genomics'], False),
                (['Life Sciences', 'Genetics and Genomics', 'Molecular Genetics'], False),
                (['Life Sciences', 'Genetics and Genomics', 'Other Genetics and Genomics'], False),
                (['Life Sciences', 'Immunology and Infectious Disease', 'Immunity'], False),
                (['Life Sciences', 'Immunology and Infectious Disease', 'Immunopathology'], False),
                (['Life Sciences', 'Immunology and Infectious Disease', 'Immunoprophylaxis and Therapy'], False),
                (['Life Sciences', 'Immunology and Infectious Disease', 'Parasitology'], False),
                (['Life Sciences', 'Marine Biology'], False),
                (['Life Sciences', 'Microbiology'], False),
                (['Life Sciences', 'Laboratory and Basic Science Research Life Sciences', 'Bacteriology'], False),
                (['Life Sciences', 'Laboratory and Basic Science Research Life Sciences', 'Environmental Microbiology and Microbial Ecology Life Sciences'], False),
                (['Life Sciences', 'Laboratory and Basic Science Research Life Sciences', 'Microbial Physiology'], False),
                (['Life Sciences', 'Laboratory and Basic Science Research Life Sciences', 'Organismal Biological Physiology'], False),
                (['Life Sciences', 'Laboratory and Basic Science Research Life Sciences', 'Pathogenic Microbiology'], False),
                (['Life Sciences', 'Laboratory and Basic Science Research Life Sciences', 'Virology'], False),
                (['Life Sciences', 'Laboratory and Basic Science Research Life Sciences', 'Other Microbiology'], False),
                (['Life Sciences', 'Nutrition', 'Comparative Nutrition'], False),
                (['Life Sciences', 'Nutrition', 'Human and Clinical Nutrition'], False),
                (['Life Sciences', 'Nutrition', 'International and Community Nutrition'], False),
                (['Life Sciences', 'Nutrition', 'Molecular, Genetic, and Biochemical Nutrition'], False),
                (['Life Sciences', 'Nutrition', 'Nutritional Epidemiology'], False),
                (['Life Sciences', 'Nutrition', 'Other Nutrition'], False),
                (['Life Sciences', 'Pharmacology, Toxicology and Environmental Health', 'Environmental Health Life Sciences'], False),
                (['Life Sciences', 'Pharmacology, Toxicology and Environmental Health', 'Medicinal Chemistry and Pharmaceutics'], False),
                (['Life Sciences', 'Pharmacology, Toxicology and Environmental Health', 'Pharmacology'], False),
                (['Life Sciences', 'Pharmacology, Toxicology and Environmental Health', 'Toxicology'], False),
                (['Life Sciences', 'Pharmacology, Toxicology and Environmental Health', 'Other Pharmacology, Toxicology and Environmental Health'], False),
                (['Life Sciences', 'Physiology', 'Cellular and Molecular Physiology'], False),
                (['Life Sciences', 'Physiology', 'Comparative and Evolutionary Physiology'], False),
                (['Life Sciences', 'Physiology', 'Endocrinology'], False),
                (['Life Sciences', 'Physiology', 'Exercise Physiology'], False),
                (['Life Sciences', 'Physiology', 'Systems and Integrative Physiology Life Sciences'], False),
                (['Life Sciences', 'Physiology', 'Other Physiology'], False),
                (['Life Sciences', 'Plant Sciences', 'Agricultural Science'], False),
                (['Life Sciences', 'Plant Sciences', 'Agronomy and Crop Sciences Life Sciences'], False),
                (['Life Sciences', 'Plant Sciences', 'Botany'], False),
                (['Life Sciences', 'Plant Sciences', 'Fruit Science'], False),
                (['Life Sciences', 'Plant Sciences', 'Horticulture'], False),
                (['Life Sciences', 'Plant Sciences', 'Plant Biology'], False),
                (['Life Sciences', 'Plant Sciences', 'Plant Breeding and Genetics Life Sciences'], False),
                (['Life Sciences', 'Plant Sciences', 'Plant Pathology'], False),
                (['Life Sciences', 'Plant Sciences', 'Weed Science'], False),
                (['Life Sciences', 'Plant Sciences', 'Other Plant Sciences'], False),
                (['Life Sciences', 'Other Life Sciences'], False),
                (['Medicine and Health Sciences', 'Alternative and Complementary Medicine'], False),
                (['Medicine and Health Sciences', 'Analytical, Diagnostic and Therapeutic Techniques and Equipment'], False),
                (['Medicine and Health Sciences', 'Systems Biology', 'Anesthesia and Analgesia'], False),
                (['Medicine and Health Sciences', 'Systems Biology', 'Diagnosis'], False),
                (['Medicine and Health Sciences', 'Systems Biology', 'Investigative Techniques'], False),
                (['Medicine and Health Sciences', 'Systems Biology', 'Surgical Procedures, Operative'], False),
                (['Medicine and Health Sciences', 'Systems Biology', 'Therapeutics'], False),
                (['Medicine and Health Sciences', 'Systems Biology', 'Other Analytical, Diagnostic and Therapeutic Techniques and Equipment'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Animal Structures'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Body Regions'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Cardiovascular System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Cells'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Digestive System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Embryonic Structures'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Endocrine System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Fluids and Secretions'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Hemic and Immune Systems'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Integumentary System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Musculoskeletal System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Nervous System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Respiratory System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Sense Organs'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Stomatognathic System'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Tissues'], False),
                (['Medicine and Health Sciences', 'Anatomy', 'Urogenital System'], False),
                (['Medicine and Health Sciences', 'Chemicals and Drugs'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Amino Acids, Peptides, and Proteins'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Biological Factors'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Biomedical and Dental Materials'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Carbohydrates'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Chemical Actions and Uses'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Complex Mixtures'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Enzymes and Coenzymes'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Heterocyclic Compounds'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Hormones, Hormone Substitutes, and Hormone Antagonists'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Inorganic Chemicals'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Lipids'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Macromolecular Substances'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Nucleic Acids, Nucleotides, and Nucleosides'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Organic Chemicals'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Pharmaceutical Preparations'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Polycyclic Compounds'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Other Chemicals and Drugs'], False),
                (['Medicine and Health Sciences', 'Communication Sciences and Disorders', 'Speech and Hearing Science'], False),
                (['Medicine and Health Sciences', 'Communication Sciences and Disorders', 'Speech Pathology and Audiology'], False),
                (['Medicine and Health Sciences', 'Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Animal Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Bacterial Infections and Mycoses'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Cardiovascular Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Congenital, Hereditary, and Neonatal Diseases and Abnormalities'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Digestive System Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Disease Modeling'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Disorders of Environmental Origin'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Endocrine System Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Eye Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Female Urogenital Diseases and Pregnancy Complications'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Hemic and Lymphatic Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Immune System Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Male Urogenital Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Musculoskeletal Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Neoplasms'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Nervous System Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Nutritional and Metabolic Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Otorhinolaryngologic Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Parasitic Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Pathological Conditions, Signs and Symptoms'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Respiratory Tract Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Skin and Connective Tissue Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Stomatognathic Diseases'], False),
                (['Medicine and Health Sciences', 'Dietetics and Clinical Nutrition', 'Virus Diseases'], False),
                (['Medicine and Health Sciences', 'Health Information Technology', 'Telemedicine'], False),
                (['Medicine and Health Sciences', 'Medical Education'], False),
                (['Medicine and Health Sciences', 'Medical Humanities'], False),
                (['Medicine and Health Sciences', 'Medical Sciences'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Biochemical Phenomena, Metabolism, and Nutrition'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Biological Phenomena, Cell Phenomena, and Immunity'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Chemical and Pharmacologic Phenomena'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Circulatory and Respiratory Physiology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Digestive, Oral, and Skin Physiology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Genetic Phenomena'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Genetic Processes'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Genetic Structures'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Anatomy'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Biochemistry'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Biomathematics and Biometrics'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Biophysics'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Biotechnology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Cell Biology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Genetics'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Immunology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Microbiology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Molecular Biology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Neurobiology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Nutrition'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Pathology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Pharmacology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Physiology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Medical Toxicology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Musculoskeletal, Neural, and Ocular Physiology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Neurosciences'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Physiological Processes'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Reproductive and Urinary Physiology'], False),
                (['Medicine and Health Sciences', 'Health and Medical Administration', 'Other Medical Sciences'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Allergy and Immunology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Anesthesiology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Cardiology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Critical Care'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Dermatology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Emergency Medicine'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Endocrinology, Diabetes, and Metabolism'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Family Medicine'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Gastroenterology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Geriatrics'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Hematology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Hepatology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Infectious Disease'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Integrative Medicine'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Internal Medicine'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Nephrology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Neurology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Obstetrics and Gynecology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Oncology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Ophthalmology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Orthopedics'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Osteopathic Medicine and Osteopathy'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Otolaryngology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Palliative Care'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Pathology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Pediatrics'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Plastic Surgery'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Podiatry'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Preventive Medicine'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Primary Care'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Psychiatry'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Pulmonology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Radiology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Rheumatology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Sports Medicine'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Surgery'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Trauma'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Urology'], False),
                (['Medicine and Health Sciences', 'Medical Specialties', 'Other Medical Specialties'], False),
                (['Medicine and Health Sciences', 'Nanotechnology', 'Nanomedicine'], False),
                (['Medicine and Health Sciences', 'Organisms'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Algae'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Animals'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Archaea'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Bacteria'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Fungi'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Mesomycetozoea'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Plants'], False),
                (['Medicine and Health Sciences', 'Optometry', 'Viruses'], False),
                (['Medicine and Health Sciences', 'Pharmacy and Pharmaceutical Sciences', 'Medicinal and Pharmaceutical Chemistry'], False),
                (['Medicine and Health Sciences', 'Pharmacy and Pharmaceutical Sciences', 'Natural Products Chemistry and Pharmacognosy'], False),
                (['Medicine and Health Sciences', 'Pharmacy and Pharmaceutical Sciences', 'Pharmaceutics and Drug Design'], False),
                (['Medicine and Health Sciences', 'Pharmacy and Pharmaceutical Sciences', 'Pharmacoeconomics and Pharmaceutical Economics'], False),
                (['Medicine and Health Sciences', 'Pharmacy and Pharmaceutical Sciences', 'Pharmacy Administration, Policy and Regulation'], False),
                (['Medicine and Health Sciences', 'Pharmacy and Pharmaceutical Sciences', 'Other Pharmacy and Pharmaceutical Sciences'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Clinical Epidemiology'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Community Health and Preventive Medicine'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Environmental Public Health'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Epidemiology'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Health and Medical Physics'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Health Services Administration'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Health Services Research'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Influenza Humans'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Influenza Virus Vaccines'], False),
                (['Medicine and Health Sciences', 'Public Health', 'International Public Health'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Maternal and Child Health'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Occupational Health and Industrial Hygiene'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Public Health Education and Promotion'], False),
                (['Medicine and Health Sciences', 'Public Health', "Women's Health"], False),
                (['Medicine and Health Sciences', 'Public Health', 'Other Public Health'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Comparative and Laboratory Animal Medicine'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Large or Food Animal and Equine Medicine'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Small or Companion Animal Medicine'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Veterinary Anatomy'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Veterinary Infectious Diseases'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Veterinary Microbiology and Immunobiology'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Veterinary Pathology and Pathobiology'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Veterinary Physiology'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Veterinary Preventive Medicine, Epidemiology, and Public Health'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Veterinary Toxicology and Pharmacology'], False),
                (['Medicine and Health Sciences', 'Veterinary Medicine', 'Other Veterinary Medicine'], False),
                (['Physical Sciences and Mathematics', 'Applied Mathematics'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Control Theory'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Dynamic Systems'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Non-linear Dynamics'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Numerical Analysis and Computation'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Ordinary Differential Equations and Applied Dynamics'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Partial Differential Equations'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Special Functions'], False),
                (['Physical Sciences and Mathematics', 'Other Medicine and Health Sciences', 'Other Applied Mathematics'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Analytical Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Environmental Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Inorganic Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Materials Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Medicinal-Pharmaceutical Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Organic Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Physical Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Polymer Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Radiochemistry'], False),
                (['Physical Sciences and Mathematics', 'Chemistry', 'Other Chemistry'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Artificial Intelligence and Robotics'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Computer Security'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Databases and Information Systems'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Graphics and Human Computer Interfaces'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Numerical Analysis and Scientific Computing'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'OS and Networks'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Programming Languages and Compilers'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Software Engineering'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Systems Architecture'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Theory and Algorithms'], False),
                (['Physical Sciences and Mathematics', 'Computer Sciences', 'Other Computer Sciences'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Biogeochemistry'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Geochemistry'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Geology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Geomorphology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Geophysics and Seismology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Glaciology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Hydrology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Mineral Physics'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Paleobiology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Paleontology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Sedimentology'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Soil Science'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Stratigraphy'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Tectonics and Structure'], False),
                (['Physical Sciences and Mathematics', 'Earth Sciences', 'Other Earth Sciences'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Environmental Education'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Environmental Health and Protection'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Environmental Indicators and Impact Assessment'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Environmental Monitoring'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Natural Resource Economics'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Natural Resources and Conservation'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Natural Resources Management and Policy'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Oil, Gas, and Energy'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Sustainability'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Water Resource Management'], False),
                (['Physical Sciences and Mathematics', 'Environmental Sciences', 'Other Environmental Sciences'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Algebra'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Algebraic Geometry'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Analysis'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Discrete Mathematics and Combinatorics'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Dynamical Systems'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Geometry and Topology'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Harmonic Analysis and Representation'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Logic and Foundations'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Number Theory'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Set Theory'], False),
                (['Physical Sciences and Mathematics', 'Mathematics', 'Other Mathematics'], False),
                (['Physical Sciences and Mathematics', 'Oceanography and Atmospheric Sciences and Meteorology', 'Atmospheric Sciences'], False),
                (['Physical Sciences and Mathematics', 'Oceanography and Atmospheric Sciences and Meteorology', 'Climate'], False),
                (['Physical Sciences and Mathematics', 'Oceanography and Atmospheric Sciences and Meteorology', 'Fresh Water Studies'], False),
                (['Physical Sciences and Mathematics', 'Oceanography and Atmospheric Sciences and Meteorology', 'Meteorology'], False),
                (['Physical Sciences and Mathematics', 'Oceanography and Atmospheric Sciences and Meteorology', 'Oceanography'], False),
                (['Physical Sciences and Mathematics', 'Oceanography and Atmospheric Sciences and Meteorology', 'Other Oceanography and Atmospheric Sciences and Meteorology'], False),
                (['Physical Sciences and Mathematics', 'Physics', 'Biological and Chemical Physics'], False),
                (['Physical Sciences and Mathematics', 'Physics', 'Elementary Particles and Fields and String Theory'], False),
                (['Physical Sciences and Mathematics', 'Physics', 'Engineering Physics'], False),
                (['Physical Sciences and Mathematics', 'Physics', 'Fluid Dynamics'], False),
                (['Physical Sciences and Mathematics', 'Physics', 'Nuclear'], False),
                (['Physical Sciences and Mathematics', 'Physics', 'Statistical, Nonlinear, and Soft Matter Physics'], False),
                (['Physical Sciences and Mathematics', 'Physics', 'Other Physics'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Applied Statistics'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Biometry'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Biostatistics'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Categorical Data Analysis'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Clinical Trials'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Design of Experiments and Sample Surveys'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Institutional and Historical'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Longitudinal Data Analysis and Time Series'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Microarrays'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Multivariate Analysis'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Probability'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Statistical Methodology'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Statistical Models'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Statistical Theory'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Survival Analysis'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Vital and Health Statistics'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Other Statistics and Probability'], False),
                (['Social and Behavioral Sciences', 'Agricultural and Resource Economics'], False),
                (['Social and Behavioral Sciences', 'Other Physical Sciences and Mathematics', 'Food Security'], False),
                (['Social and Behavioral Sciences', 'Anthropology'], False),
                (['Social and Behavioral Sciences', 'Animal Studies', 'Archaeological Anthropology'], False),
                (['Social and Behavioral Sciences', 'Animal Studies', 'Biological and Physical Anthropology'], False),
                (['Social and Behavioral Sciences', 'Animal Studies', 'Folklore'], False),
                (['Social and Behavioral Sciences', 'Animal Studies', 'Linguistic Anthropology'], False),
                (['Social and Behavioral Sciences', 'Animal Studies', 'Social and Cultural Anthropology'], False),
                (['Social and Behavioral Sciences', 'Animal Studies', 'Other Anthropology'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Broadcast and Video Studies'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Communication Technology and New Media'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Critical and Cultural Studies'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Gender, Race, Sexuality, and Ethnicity in Communication'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Graphic Communications'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Health Communication'], False),
                (['Social and Behavioral Sciences', 'Communication', 'International and Intercultural Communication'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Interpersonal and Small Group Communication'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Journalism Studies'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Mass Communication'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Organizational Communication'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Public Relations and Advertising'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Publishing'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Social Influence and Political Communication'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Social Media'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Speech and Rhetorical Studies'], False),
                (['Social and Behavioral Sciences', 'Communication', 'Other Communication'], False),
                (['Social and Behavioral Sciences', 'Counseling', 'Counselor Education'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Behavioral Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Econometrics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Economic History'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Economic Theory'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Finance'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Growth and Development'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Health Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Income Distribution'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Industrial Organization'], False),
                (['Social and Behavioral Sciences', 'Economics', 'International Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Labor Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Macroeconomics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Political Economy'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Public Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Regional Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Other Economics'], False),
                (['Social and Behavioral Sciences', 'Geography'], False),
                (['Social and Behavioral Sciences', 'Environmental Studies', 'Geographic Information Sciences'], False),
                (['Social and Behavioral Sciences', 'Environmental Studies', 'Human Geography'], False),
                (['Social and Behavioral Sciences', 'Environmental Studies', 'Nature and Society Relations'], False),
                (['Social and Behavioral Sciences', 'Environmental Studies', 'Physical and Environmental Geography'], False),
                (['Social and Behavioral Sciences', 'Environmental Studies', 'Remote Sensing'], False),
                (['Social and Behavioral Sciences', 'Environmental Studies', 'Spatial Science'], False),
                (['Social and Behavioral Sciences', 'Environmental Studies', 'Other Geography'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Archival Science'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Cataloging and Metadata'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Collection Development and Management'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Information Literacy'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Scholarly Communication'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Scholarly Publishing'], False),
                (['Social and Behavioral Sciences', 'Public Affairs, Public Policy and Public Administration'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Economic Policy'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Education Policy'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Emergency and Disaster Management'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Energy Policy'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Environmental Policy'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Health Policy'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Infrastructure'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Policy Design, Analysis, and Evaluation'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Policy History, Theory, and Methosd'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Science and Technology Policy'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Social Policy'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Social Welfare'], False),
                (['Social and Behavioral Sciences', 'Organization Development', 'Other Public Affairs, Public Policy and Public Administration'], False),
                (['Social and Behavioral Sciences', 'Social Statistics'], False),
                (['Social and Behavioral Sciences', 'Social Work'], False),
                (['Social and Behavioral Sciences', 'Sociology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Civic and Community Engagement'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Community-based Learning'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Community-based Research'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Criminology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Demography, Population, and Ecology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Domestic and Intimate Partner Violence'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Educational Sociology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Family, Life Course, and Society'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Gender and Sexuality'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Gerontology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Human Ecology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Inequality and Stratification'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Medicine and Health'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Place and Environment'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Politics and Social Change'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Quantitative, Qualitative, Comparative, and Historical Methodologies'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Race and Ethnicity'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Regional Sociology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Rural Sociology'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Service Learning'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Social Psychology and Interaction'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Sociology of Culture'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Sociology of Religion'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Theory, Knowledge and Science'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Tourism'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Work, Economy and Organizations'], False),
                (['Social and Behavioral Sciences', 'Science and Technology Studies', 'Other Sociology'], False),
                (['Social and Behavioral Sciences', 'Other Social and Behavioral Sciences'], False)
            ]
        },
        'bitss': {
            '_id': 'bitss',
            'name': 'BITSS',
            'share_publish_type': 'Preprint',
            'description': 'An interdisciplinary archive of articles focused on improving research transparency and reproducibility',
            'domain': '',  # Not using domain
            'domain_redirect_enabled': False,
            'external_url': 'http://www.bitss.org',
            'example': '',
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Steering Committee</h2>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li>Edward Miguel (UC Berkeley)</li>
                        <li>Garret Christensen</li>
                        <li>Kelsey Mulcahy</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li>Temina Madon</li>
                        <li>Jennifer Sturdy (BITSS)</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+bitss@osf.io',
            'email_support': 'support+bitss@osf.io',
            'social_twitter': 'UCBITSS',
            'default_license': 'CC-By Attribution 4.0 International',
            'licenses_acceptable': ['CC-By Attribution 4.0 International', 'CC0 1.0 Universal'],
            'subjects_acceptable': [
                (['Medicine and Health Sciences', 'Health Information Technology'], False),
                (['Medicine and Health Sciences', 'Mental and Social Health'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Animal-Assisted Therapy'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Art Therapy'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Clinical and Medical Social Work'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Cognitive Behavioral Therapy'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Community Health'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Marriage and Family Therapy and Counseling'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Psychiatric and Mental Health'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Psychoanalysis and Psychotherapy'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Substance Abuse and Addiction'], False),
                (['Medicine and Health Sciences', 'Bioethics and Medical Ethics', 'Other Mental and Social Health'], False),
                (['Medicine and Health Sciences', 'Psychiatry and Psychology', 'Behavior and Behavior Mechanisms'], False),
                (['Medicine and Health Sciences', 'Psychiatry and Psychology', 'Behavioral Disciplines and Activities'], False),
                (['Medicine and Health Sciences', 'Psychiatry and Psychology', 'Dance Movement Therapy'], False),
                (['Medicine and Health Sciences', 'Psychiatry and Psychology', 'Mental Disorders'], False),
                (['Medicine and Health Sciences', 'Psychiatry and Psychology', 'Psychological Phenomena and Processes'], False),
                (['Medicine and Health Sciences', 'Psychiatry and Psychology', 'Other Psychiatry and Psychology'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Clinical Epidemiology'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Community Health and Preventive Medicine'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Environmental Public Health'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Epidemiology'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Health and Medical Physics'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Health Services Administration'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Health Services Research'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Influenza Humans'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Influenza Virus Vaccines'], False),
                (['Medicine and Health Sciences', 'Public Health', 'International Public Health'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Maternal and Child Health'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Occupational Health and Industrial Hygiene'], False),
                (['Medicine and Health Sciences', 'Public Health', 'Public Health Education and Promotion'], False),
                (['Medicine and Health Sciences', 'Public Health', "Women's Health"], False),
                (['Medicine and Health Sciences', 'Public Health', 'Other Public Health'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Applied Statistics'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Biometry'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Biostatistics'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Categorical Data Analysis'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Clinical Trials'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Design of Experiments and Sample Surveys'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Institutional and Historical'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Longitudinal Data Analysis and Time Series'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Microarrays'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Multivariate Analysis'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Probability'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Statistical Methodology'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Statistical Models'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Statistical Theory'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Survival Analysis'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Vital and Health Statistics'], False),
                (['Physical Sciences and Mathematics', 'Statistics and Probability', 'Other Statistics and Probability'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Behavioral Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Econometrics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Economic History'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Economic Theory'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Finance'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Growth and Development'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Health Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Income Distribution'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Industrial Organization'], False),
                (['Social and Behavioral Sciences', 'Economics', 'International Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Labor Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Macroeconomics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Political Economy'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Public Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Regional Economics'], False),
                (['Social and Behavioral Sciences', 'Economics', 'Other Economics'], False),
                (['Social and Behavioral Sciences', 'Legal Studies', 'Criminology and Criminal Justice'], False),
                (['Social and Behavioral Sciences', 'Legal Studies', 'Forensic Science and Technology'], False),
                (['Social and Behavioral Sciences', 'Legal Studies', 'Legal Theory'], False),
                (['Social and Behavioral Sciences', 'Legal Studies', 'Other Legal Studies'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Archival Science'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Cataloging and Metadata'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Collection Development and Management'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Information Literacy'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Scholarly Communication'], False),
                (['Social and Behavioral Sciences', 'Library and Information Science', 'Scholarly Publishing'], False),
                (['Social and Behavioral Sciences', 'Political Science', 'American Politics'], False),
                (['Social and Behavioral Sciences', 'Political Science', 'Comparative Politics'], False),
                (['Social and Behavioral Sciences', 'Political Science', 'International Relations'], False),
                (['Social and Behavioral Sciences', 'Political Science', 'Models and Methods'], False),
                (['Social and Behavioral Sciences', 'Political Science', 'Political Theory'], False),
                (['Social and Behavioral Sciences', 'Political Science', 'Other Political Science'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Applied Behavior Analysis'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Biological Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Child Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Clinical Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Cognition and Perception'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Cognitive Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Community Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Counseling Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Developmental Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Experimental Analysis of Behavior'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Health Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Industrial and Organizational Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Multicultural Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Pain Management'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Personality and Social Contexts'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Quantitative Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'School Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Social Psychology'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Theory and Philosophy'], False),
                (['Social and Behavioral Sciences', 'Psychology', 'Other Psychology'], False),
                (['Social and Behavioral Sciences', 'Sociology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Civic and Community Engagement'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Community-based Learning'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Community-based Research'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Criminology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Demography, Population, and Ecology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Domestic and Intimate Partner Violence'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Educational Sociology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Family, Life Course, and Society'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Gender and Sexuality'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Gerontology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Human Ecology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Inequality and Stratification'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Medicine and Health'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Place and Environment'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Politics and Social Change'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Quantitative, Qualitative, Comparative, and Historical Methodologies'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Race and Ethnicity'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Regional Sociology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Rural Sociology'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Service Learning'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Social Control, Law, Crime, and Deviance'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Social Psychology and Interaction'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Sociology of Culture'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Sociology of Religion'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Theory, Knowledge and Science'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Tourism'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Work, Economy and Organizations'], False),
                (['Social and Behavioral Sciences', 'Social Statistics', 'Other Sociology'], False),
                (['Physical Sciences and Mathematics', 'Other Physical Sciences and Mathematics'], False),
                (['Medicine and Health Sciences', 'Other Medicine and Health Sciences'], False),
                (['Social and Behavioral Sciences', 'Other Social and Behavioral Sciences'], False)
            ]
        }
    }

    preprint_providers_to_add = STAGING_PREPRINT_PROVIDERS if env == 'stage' else PROD_PREPRINT_PROVIDERS
    with transaction.atomic():
        for provider_id in preprint_providers_to_add:
            update_or_create(PREPRINT_PROVIDERS[provider_id])


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    env = str(sys.argv[1]).lower() if len(sys.argv) == 2 else False
    if not env:
        env = 'prod'
    elif env not in ENVS:
        print('A specified environment must be one of: {}'.format(ENVS))
        sys.exit(1)
    main(env)
