# -*- coding: utf-8 -*-
"""Fake data generator.

To use:

1. Install fake-factory.

    pip install fake-factory

2. Create your OSF user account

3. Run the script, passing in your username (email).
::

    python -m scripts.create_fakes --user fred@cos.io

This will create 3 fake public projects, each with 3 fake contributors (with
    you as the creator).

To create a project with a complex component structure, pass in a list representing the depth you would
like each component to contain.
Examples:
    python -m scripts.create_fakes -u fred@cos --components '[1, 1, 1, 1]' --nprojects 1
...will create a project with 4 components.
    python -m scripts.create_fakes -u fred@cos --components '4' --nprojects 1
...will create a project with a series of components, 4 levels deep.
    python -m scripts.create_fakes -u fred@cos --components '[1, [1, 1]]' --nprojects 1
...will create a project with two top level components, and one with a depth of 2 components.

"""
from __future__ import print_function, absolute_import
import ast
import sys
import argparse
import logging
import random
from modularodm.query.querydialect import DefaultQueryDialect as Q
from faker import Factory

from framework.auth import Auth
from website.app import init_app
from website import models, security
from framework.auth import utils
from tests.factories import UserFactory, ProjectFactory, NodeFactory
from faker.providers import BaseProvider

rapper_list = ('Ab-Soul',
               'Aceyalone', 'The Alkaholiks', 'Alchemist', 'Akwid', 'B[edit]', 'B-Real', 'Bad Azz', 'Big Syke',
               'Blu', 'Brownside', 'Busdriver', 'C[edit]', 'Cali Swag District', 'Captain Murphy', 'Casey Veggies',
               'Chali 2na', 'Chiddy', 'clipping.', 'Cozz', 'Crooked i', 'Cypress Hill', 'D[edit]', 'The D.O.C.',
               'Daz Dillinger', 'Defari', 'Deuce', 'Dilated Peoples', 'DJ Mustard (producer)', 'DJ Yella',
               'Dom Kennedy',
               'Domo Genesis', 'Dr. Dre', 'Dudley Perkins', 'Dumbfoundead', 'E[edit]', 'Tha Eastsidaz', 'Eazy E',
               'Eligh',
               'Evidence', 'Earl Sweatshirt', 'F[edit]', 'Fatlip', 'Freestyle Fellowship', 'G[edit]', 'The Game',
               'Giant Panda',
               'Gift of Gab', 'Guerilla Black', 'The Grouch', 'goldie loc', 'H[edit]', 'Haiku DEtat', 'Hodgy Beats',
               'Hopsin',
               'I[edit]', 'Ice Cube', 'Ice-T', 'Imani', 'J[edit]', 'Jay Rock', 'Jurassic 5', 'Justin Warfield', 'J-Ro',
               'K[edit]',
               'Kendrick Lamar', 'The Kid', 'Kid Frost', 'Kid Ink', 'Knoc-turnal', 'Kokane', 'Kurupt', 'King Tee',
               'L[edit]',
               'L.A.M.B', 'L.A. Symphony', 'Lil Eazy E', 'Lootpack', 'M[edit]', 'Madlib', 'MC Ren', 'Mike G',
               'Mike Shinoda', 'Murs',
               'N[edit]', 'N.W.A', 'Nipsey Hussle', 'Nick Taylor', 'O[edit]', 'Oh No', 'P[edit]', 'Pac Div',
               'People Under The Stairs',
               'Phora', 'Pigeon John', 'The Pharcyde', 'Problem (rapper)', 'Psychosiz', 'Psycho Realm', 'RJ ',
               'Ras Kass', 'RBX', 'S[edit]',
               'ScHoolboy Q', 'Sen Dog', 'Skeme', 'Snoop Dogg', 'South Central Cartel', 'Spider Loc', 'Self Provoked',
               'T[edit]', 'Thurzday',
               'Truth', 'Tweedy Bird Loc', 'Tyga', '"Tyler, The Creator"', 'Tupac Shakur', 'U[edit]', 'Ugly Duckling',
               'U-N-I', 'V[edit]', 'Lil Wayne',
               'Riff Raff',)


class Sciencer(BaseProvider):
    # Science term Faker Provider created by @csheldonhess
    # https://github.com/csheldonhess/FakeConsumer/blob/master/faker/providers/science.py
    word_list = ('tuna fish', 'ludicrous', 'doin this spaghetti', 'Serengeti', 'Eveready incomplete', 'sink and weep',
                 'toilet seat back street',
                 'track meet', 'thats neat!', 'half beat dictionary', 'pictionary', 'fictions scary',
                 'esophagus', 'preposterous', 'sarcophagus',
                 'Ninja Turtles', 'jumpin hurdles', 'flippin gerbils',
                 'frat boys', 'fat goys', 'that noise',
                 'satchel', 'at you (atchoo)', 'Achoo! (sneeze)',
                 'real gentle stillness', 'severe mental illness',
                 'international hostel', 'supernatural nostril', 'fantastical raw wool the tightest flow on the planet',
                 'the righteous dont panic', 'the whitest known granite',
                 'Oil of Olay', 'spoil the day', 'foiled and played',
                 'egg yolks in your eyes', 'dead folks say goodbye', 'you choked on your lines',
                 'lackluster', 'just clutter', 'colonel mustard',
                 'worldwide stage', 'real tight cage', 'just got paid',
                 'listen to that', 'stick in your back', 'hit you so fast',
                 'rhyming words', 'flying herds', 'mining for turds',
                 'Houston Texas', 'whos goin', 'test this', 'goose for breakfast',
                 'IHOP', 'hi-tops', 'why not', 'my doc', 'flip flop', 'I bought', 'cyclops', 'eye sock(et)',
                 'cry a lot',
                 'waffle House', 'awful blouse',
                 'Doritos', 'youre weak homes -more meat yo',
                 'Batman', 'flat plan', 'back hand', 'fat tan',
                 'Magical Mystery Tour', 'mad youll hit me your bore', 'battle your sister for pork',
                 'major fail', 'save your mail', 'play the scale', 'filleted the snail',
                 'for the win', 'born again', 'pour the gin', 'tortoise shin',
                 'okey dokey', 'dont ye choke me', 'soapy coke please',
                 'The Week in Rap', 'hes cheap and fat, please meet my dad, youre sweet in plaid', 'A crapella',
                 'Amazeballs',
                 'Ann Curry-ed', 'Awesome sauce', 'Baby bump', 'Baller', 'Beleiber', 'Bitcoin', 'Blamestorming',
                 'Boomerang child', 'Bootylicious',
                 'Bromance', 'Bropocalypse', 'C-note', 'Cougar', 'Crunk', 'Cyberslacking', 'Dawg', 'Designated drunk',
                 'Driving the Bronco',
                 'Duck face', 'Dude', 'Dweet', 'Earjacking', 'Earmuffs', 'Ego surfing', 'Fanboi/fangirl', 'Fauxpology',
                 'Foodie', 'Frak',
                 'Frankenfood', 'Freak flag', 'Friend zone', 'Fro-yo', 'Gaydar', 'Girl crush', 'Grrrl', 'Hangry',
                 'Helicopter parent', 'Hipster',
                 'Hot mess', 'Humblebrag', 'Jailbait', 'Karaoke filibuster', 'Kicks', 'Knosh', 'Legendary', 'LOL',
                 'Ludwigvanquixote', 'Make it rain',
                 'Man cave', 'Meat sweats', 'Nom', 'Nontroversy', 'NSFW', 'OM(F)G!', 'On a boat', 'One-upper',
                 'Party foul', 'Phat', 'Please advise',
                 'Pregret', 'Pwned', 'Quantum physics', 'Ratchet', 'Rendezbooze', 'Rickroll', 'Said no one ever',
                 'Salmon', 'Selfie', 'Sext', 'Skrill',
                 'Snail mail', 'Sniff test', 'Swag', 'Sweet', 'Thats what she said', 'Trout', 'Twerk', 'Typeractive',
                 'Upskirt', 'Virgin ears', 'W00t!',
                 'Word out', 'WTF', 'X-factor', 'YOLO', 'Zombie ad',)

    def science_word(cls):
        """
        :example 'Lorem'
        """
        return cls.random_element(cls.word_list)

    def science_words(cls, nb=3):
        """
        Generate an array of random words
        :example array('Lorem', 'ipsum', 'dolor')
        :param nb how many words to return
        """
        return [cls.science_word() for _ in range(0, nb)]

    def science_sentence(cls, nb_words=6, variable_nb_words=True):
        """
        Generate a random sentence
        :example 'Lorem ipsum dolor sit amet.'
        :param nb_words around how many words the sentence should contain
        :param variable_nb_words set to false if you want exactly $nbWords returned,
            otherwise $nbWords may vary by +/-40% with a minimum of 1
        """
        if nb_words <= 0:
            return ''

        if variable_nb_words:
            nb_words = cls.randomize_nb_elements(nb_words)

        words = cls.science_words(nb_words)
        words[0] = words[0].title()

        return " ".join(words) + '.'

    def science_sentences(cls, nb=3):
        """
        Generate an array of sentences
        :example array('Lorem ipsum dolor sit amet.', 'Consectetur adipisicing eli.')
        :param nb how many sentences to return
        :return list
        """
        return [cls.science_sentence() for _ in range(0, nb)]

    def science_paragraph(cls, nb_sentences=3, variable_nb_sentences=True):
        """
        Generate a single paragraph
        :example 'Sapiente sunt omnis. Ut pariatur ad autem ducimus et. Voluptas rem voluptas sint modi dolorem amet.'
        :param nb_sentences around how many sentences the paragraph should contain
        :param variable_nb_sentences set to false if you want exactly $nbSentences returned,
            otherwise $nbSentences may vary by +/-40% with a minimum of 1
        :return string
        """
        if nb_sentences <= 0:
            return ''

        if variable_nb_sentences:
            nb_sentences = cls.randomize_nb_elements(nb_sentences)

        return " ".join(cls.science_sentences(nb_sentences))

    def science_paragraphs(cls, nb=3):
        """
        Generate an array of paragraphs
        :example array($paragraph1, $paragraph2, $paragraph3)
        :param nb how many paragraphs to return
        :return array
        """
        return [cls.science_paragraph() for _ in range(0, nb)]

    def science_text(cls, max_nb_chars=200):
        """
        Generate a text string.
        Depending on the $maxNbChars, returns a string made of words, sentences, or paragraphs.
        :example 'Sapiente sunt omnis. Ut pariatur ad autem ducimus et. Voluptas rem voluptas sint modi dolorem amet.'
        :param max_nb_chars Maximum number of characters the text should contain (minimum 5)
        :return string
        """
        text = []
        if max_nb_chars < 5:
            raise ValueError('text() can only generate text of at least 5 characters')

        if max_nb_chars < 25:
            # join words
            while not text:
                size = 0
                # determine how many words are needed to reach the $max_nb_chars once;
                while size < max_nb_chars:
                    word = (' ' if size else '') + cls.science_word()
                    text.append(word)
                    size += len(word)
                text.pop()
            text[0] = text[0][0].upper() + text[0][1:]
            last_index = len(text) - 1
            text[last_index] += '.'
        elif max_nb_chars < 100:
            # join sentences
            while not text:
                size = 0
                # determine how many sentences are needed to reach the $max_nb_chars once
                while size < max_nb_chars:
                    sentence = (' ' if size else '') + cls.science_sentence()
                    text.append(sentence)
                    size += len(sentence)
                text.pop()
        else:
            # join paragraphs
            while not text:
                size = 0
                # determine how many paragraphs are needed to reach the $max_nb_chars once
                while size < max_nb_chars:
                    paragraph = ('\n' if size else '') + cls.science_paragraph()
                    text.append(paragraph)
                    size += len(paragraph)
                text.pop()

        return "".join(text)


logger = logging.getLogger('create_fakes')
logging.basicConfig(level=logging.ERROR)
fake = Factory.create()
fake.add_provider(Sciencer)


def create_fake_user():
    email = fake.email()
    name = random.choice(rapper_list)
    parsed = utils.impute_names(name)
    user = UserFactory(username=email, fullname=name,
                       is_registered=True, is_claimed=True,
                       verification_key=security.random_string(15),
                       date_registered=fake.date_time(),
                       emails=[email],
                       **parsed
                       )
    user.set_password('faker123')
    user.save()
    logger.info('Created user: {0} <{1}>'.format(user.fullname, user.username))
    return user


def parse_args():
    parser = argparse.ArgumentParser(description='Create fake data.')
    parser.add_argument('-u', '--user', dest='user', required=True)
    parser.add_argument('--nusers', dest='n_users', type=int, default=3)
    parser.add_argument('--nprojects', dest='n_projects', type=int, default=3)
    parser.add_argument('-c', '--components', dest='n_components', type=evaluate_argument, default='0')
    parser.add_argument('-p', '--privacy', dest="privacy", type=str, default='private', choices=['public', 'private'])
    parser.add_argument('-n', '--name', dest='name', type=str, default=None)
    parser.add_argument('-t', '--tags', dest='n_tags', type=int, default=5)
    parser.add_argument('--presentation', dest='presentation_name', type=str, default=None)
    return parser.parse_args()


def evaluate_argument(string):
    return ast.literal_eval(string)


def create_fake_project(creator, n_users, privacy, n_components, name, n_tags, presentation_name):
    auth = Auth(user=creator)
    project_title = name if name else fake.science_sentence()
    project = ProjectFactory(title=project_title, description=fake.science_paragraph(), creator=creator)
    project.set_privacy(privacy)
    for _ in range(n_users):
        contrib = create_fake_user()
        project.add_contributor(contrib, auth=auth)
    if isinstance(n_components, int):
        for _ in range(n_components):
            NodeFactory(project=project, title=fake.science_sentence(), description=fake.science_paragraph(),
                        creator=creator)
    elif isinstance(n_components, list):
        render_generations_from_node_structure_list(project, creator, n_components)
    for _ in range(n_tags):
        project.add_tag(fake.science_word(), auth=auth)
    if presentation_name is not None:
        project.add_tag(presentation_name, auth=auth)
        project.add_tag('poster', auth=auth)

    project.save()
    logger.info('Created project: {0}'.format(project.title))
    return project


def render_generations_from_parent(parent, creator, num_generations):
    current_gen = parent
    for generation in xrange(0, num_generations):
        next_gen = NodeFactory(
                parent=current_gen,
                creator=creator,
                title=fake.science_sentence(),
                description=fake.science_paragraph()
        )
        current_gen = next_gen
    return current_gen


def render_generations_from_node_structure_list(parent, creator, node_structure_list):
    new_parent = None
    for node_number in node_structure_list:
        if isinstance(node_number, list):
            render_generations_from_node_structure_list(new_parent or parent, creator, node_number)
        else:
            new_parent = render_generations_from_parent(parent, creator, node_number)
    return new_parent


def main():
    args = parse_args()
    creator = models.User.find(Q('username', 'eq', args.user))[0]
    for i in range(args.n_projects):
        name = args.name + str(i) if args.name else ''
        create_fake_project(creator, args.n_users, args.privacy, args.n_components, name, args.n_tags,
                            args.presentation_name)
    print('Created {n} fake projects.'.format(n=args.n_projects))
    sys.exit(0)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()
