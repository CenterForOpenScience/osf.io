#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Preprint Provicer elements"""

import logging
import sys

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.models import Subject, PreprintProvider, NodeLicense

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SUBJECTS_CACHE = {}

def get_subject_id(name):
    if not name in SUBJECTS_CACHE:
        subject = None
        try:
            subject = Subject.find_one(Q('text', 'eq', name))
        except NoResultsFound:
            raise Exception('Subject: "{}" not found'.format(name))
        else:
            SUBJECTS_CACHE[name] = subject._id

    return SUBJECTS_CACHE[name]

def get_license(name):
    try:
        license = NodeLicense.find_one(Q('name', 'eq', name))
    except NoResultsFound:
        raise Exception('License: "{}" not found'.format(name))
    return license

def update_or_create(provider_data):
    provider = PreprintProvider.load(provider_data['_id'])
    if provider:
        provider_data['subjects_acceptable'] = map(
            lambda rule: (map(get_subject_id, rule[0]), rule[1]),
            provider_data['subjects_acceptable']
        )
        provider_data['licenses_acceptable'] = [get_license(name) for name in provider_data['licenses_acceptable']]
        for key, val in provider_data.iteritems():
            setattr(provider, key, val)
        changed_fields = provider.save()
        if changed_fields:
            print('Updated {}: {}'.format(provider.name, changed_fields))
        return provider, False
    else:
        new_provider = PreprintProvider(**provider_data)
        new_provider.save()
        provider = PreprintProvider.load(new_provider._id)
        print('Added new preprint provider: {}'.format(provider._id))
        return new_provider, True

def main():
    use_plos = '--plos' in sys.argv

    PREPRINT_PROVIDERS = [
        {
            '_id': 'osf',
            'name': 'Open Science Framework',
            'logo_name': 'cos-logo.png',
            'description': 'A scholarly commons to connect the entire research cycle',
            'banner_name': 'cos-banner.png',
            'external_url': 'https://osf.io/preprints/',
            'example': 'khbvy',
            'advisory_board': '',
            'email_contact': '',
            'email_support': '',
            'social_twitter': '',
            'social_facebook': '',
            'social_instagram': '',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'header_text': '',
            'subjects_acceptable': [],
        },
        {
            '_id': 'engrxiv',
            'name': 'engrXiv',
            'logo_name': 'engrxiv-logo.png',
            'description': 'The open archive of engineering.',
            'banner_name': 'engrxiv-banner.png',
            'external_url': 'http://engrxiv.org',
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
                        <li><a href="http://www.douglasvanbossuyt.com/">Douglas Van Bossuyt</a>, mechanical engineer, Colorado School of Mines</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+engrxiv@osf.io',
            'email_support': 'support+engrxiv@osf.io',
            'social_twitter': 'engrxiv',
            'social_facebook': 'engrXiv',
            'social_instagram': 'engrxiv',
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'header_text': '',
            'subjects_acceptable': [
                (['Computer and information sciences', 'Software engineering'], True),
                (['Engineering and technology'], True),
            ] if use_plos else [
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
        {
            '_id': 'psyarxiv',
            'name': 'PsyArXiv',
            'logo_name': 'psyarxiv-logo.png',
            'description': 'A free preprint service for the psychological sciences.',
            'banner_name': 'psyarxiv-banner.png',
            'external_url': 'http://psyarxiv.com',
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
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'header_text': '',
            'subjects_acceptable': [
                (['Social and behavioral sciences'], True),
                (['Arts and Humanities'], True),
            ] if use_plos else [
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
        {
            '_id': 'socarxiv',
            'name': 'SocArXiv',
            'logo_name': 'socarxiv-logo.png',
            'description': 'Open archive of the social sciences',
            'banner_name': 'socarxiv-banner.png',
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
            'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
            'header_text': '',
            'subjects_acceptable': [
                (['Arts and Humanities'], True),
                (['Education'], True),
                (['Law'], True),
                (['Social and behavioral sciences'], True),
            ] if use_plos else [
                (['Arts and Humanities'], True),
                (['Education'], True),
                (['Law'], True),
                (['Social and Behavioral Sciences'], True),
            ],
        },
    ]

    with TokuTransaction():
        for provider_data in PREPRINT_PROVIDERS:
            update_or_create(provider_data)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()
