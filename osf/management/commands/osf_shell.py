"""Enhanced python shell.
Includes all features from django-extension's shell_plus command plus OSF-specific
niceties.

By default, sessions run in a transaction, so changes won't be commited until
you execute `commit()`.

All models are imported by default, as well as common OSF and Django objects.

To add more objects, set the `OSF_SHELL_USER_IMPORTS` Django setting
to a dictionary or a callable that returns a dictionary.

Example: ::

    from django.apps import apps

    def get_user_imports():
        User = apps.get_model('osf.OSFUser')
        Node = apps.get_model('osf.AbstractNode')
        me = User.objects.get(username='sloria1@gmail.com')
        node = Node.objects.first()
        return {
            'me': me,
            'node': node,
        }

    OSF_SHELL_USER_IMPORTS = get_user_imports
"""
from django.conf import settings
from django.db import transaction
from django.utils.termcolors import colorize
from django.db.models import Model
from django_extensions.management.commands import shell_plus
from django_extensions.management.utils import signalcommand
from elasticsearch_metrics.registry import registry as metrics_registry


def header(text):
    return colorize(text, fg='green', opts=('bold', ))

def format_imported_objects(models, metrics, osf, transaction, other, user):
    def format_dict(d):
        return ', '.join(sorted(d.keys()))
    ret = """
{models_header}
{models}

{metrics_header}
{metrics}

{osf_header}
{osf}

{transaction_header}
{transaction}

{other_header}
{other}""".format(
        models_header=header('Models:'),
        models=format_dict(models),
        metrics_header=header('Metrics:'),
        metrics=format_dict(metrics),
        osf_header=header('OSF:'),
        osf=format_dict(osf),
        transaction_header=header('Transaction:'),
        transaction=format_dict(transaction),
        other_header=header('Django:'),
        other=format_dict(other),
    )
    if user:
        ret += '\n\n{user_header}\n{user}'.format(
            user_header=header('User Imports:'),
            user=format_dict(user)
        )
    return ret


# kwargs will be the grouped imports, e.g. {'models': {...}, 'osf': {...}}
def make_banner(auto_transact=True, **kwargs):
    logo = """
                    .+yhhys/`
                `smmmmmmmmd:
        `--.`    ommmmmmmmmmm.   `.--.
    `odmmmmmh/  smmmhhyhdmmm- :ymmmmmdo.
    -dmmmmmmmmmy .hho+++++sdo smmmmmmmmmm:
    smmmmmmmmmmm: `++++++++: -mmmmmmmmmmmy
    +mmmmmmmmmmmo: :+++++++.:+mmmmmmmmmmmo
    +dmmmmmmmds++. .://:-``++odmmmmmmmmo
        `:osyhys+++/          :+++oyhyso/`
`/shddds/``.-::-.            `-::-.``/shdddy/`
-dmmmmmds++++/.                  ./++++sdmmmmmd:
hmmmmmmo+++++++.                .++++++++dmmmmmd`
hmmmmmmo+++++++.                .++++++++dmmmmmd`
-dmmmmmds++++/.                  ./++++sdmmmmmd:
`/shddhs/``.-::-.            `-::-.``/shdddy/`
        `:osyhys+++/          :+++oyhyso/`
    +dmmmmmmmds++. .://:- `++odmmmmmmmmo
    +mmmmmmmmmmmo: /++++++/`:+mmmmmmmmmmmo
    smmmmmmmmmmm: `++++++++. -mmmmmmmmmmmy
    -dmmmmmmmmmy  `s++++++y/  smmmmmmmmmm:
    `odmmmmmh/   hmmhyyhdmm/  :ymmmmmds.
        `--.`    `mmmmmmmmmmo    `.--.
                    /mmmmmmmmh`
                    `+shhyo:
    """
    greeting = 'Welcome to the OSF Shell. Happy hacking!'
    imported_objects = format_imported_objects(**kwargs)
    transaction_warning = """
*** TRANSACTION AUTOMATICALLY STARTED ***
To persist changes, run 'commit()'.
Keep in mind that changing documents will lock them.
This feature can be disabled with the '--no-transaction' flag."""
    no_transaction_warning = """
*** AUTO-TRANSACTION DISABLED ***
All changes will persist. Transactions must be handled manually."""
    template = """{logo}
{greeting}
{imported_objects}
{warning}
"""
    if auto_transact:
        warning = colorize(transaction_warning, fg='yellow')
    else:
        warning = colorize(no_transaction_warning, fg='red')
    return template.format(
        logo=colorize(logo, fg='cyan'),
        greeting=colorize(greeting, opts=('bold', )),
        imported_objects=imported_objects,
        warning=warning,
    )


class Command(shell_plus.Command):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--no-transaction', action='store_false', dest='transaction',
            help="Don't run session in transaction. Transactions must be "
                 'started manually with start_transaction()'
        )

    def get_osf_imports(self):
        """Return a dictionary of common OSF objects and utilities."""
        from osf.management.utils import print_sql
        from website import settings as website_settings
        from framework.auth import Auth, get_user
        ret = {
            'print_sql': print_sql,
            'Auth': Auth,
            'get_user': get_user,
            'website_settings': website_settings,
        }
        try:  # faker isn't a prod requirement
            from faker import Factory
        except ImportError:
            pass
        else:
            fake = Factory.create()
            ret['fake'] = fake
        return ret

    def get_metrics(self):
        return {
            each.__name__: each
            for each in metrics_registry.get_metrics()
        }

    def get_grouped_imports(self, options):
        """Return a dictionary of grouped import of the form:
        {
            'osf': {
                'Auth': <framework.auth.Auth>,
                ....
            }
            'models': {...}
            'transaction': {...}
            'other': {...}
        }
        """
        auto_transact = options.get('transaction', True)

        def start_transaction():
            self.atomic.__enter__()
            print('New transaction opened.')

        def commit():
            self.atomic.__exit__(None, None, None)
            print('Transaction committed.')
            if auto_transact:
                start_transaction()

        def rollback():
            exc_type = RuntimeError
            exc_value = exc_type('Transaction rollback')
            self.atomic.__exit__(exc_type, exc_value, None)
            print('Transaction rolled back.')
            if auto_transact:
                start_transaction()

        groups = {
            'models': {},
            'metrics': self.get_metrics(),
            'other': {},
            'osf': self.get_osf_imports(),
            'transaction': {
                'start_transaction': start_transaction,
                'commit': commit,
                'rollback': rollback,
            },
            'user': self.get_user_imports(),
        }
        # Import models and common django imports
        shell_plus_imports = shell_plus.Command.get_imported_objects(self, options)
        for name, object in shell_plus_imports.items():
            if isinstance(object, type) and issubclass(object, Model):
                groups['models'][name] = object
            else:
                groups['other'][name] = object

        return groups

    def get_user_imports(self):
        imports = getattr(settings, 'OSF_SHELL_USER_IMPORTS', None)
        if imports:
            if callable(imports):
                imports = imports()
            return imports
        else:
            return {}

    # Override shell_plus.Command
    def get_imported_objects(self, options):
        # Merge all the values of grouped_imports
        imported_objects = {}
        for imports in self.grouped_imports.values():
            imported_objects.update(imports)
        return imported_objects

    # Override shell_plus.Command
    @signalcommand
    def handle(self, *args, **options):
        self.atomic = transaction.atomic()
        auto_transact = options.get('transaction', True)
        options['quiet_load'] = True  # Don't show default shell_plus banner
        self.grouped_imports = self.get_grouped_imports(options)
        banner = make_banner(auto_transact=auto_transact, **self.grouped_imports)
        print(banner)
        if auto_transact:
            self.atomic.__enter__()
        super(Command, self).handle(*args, **options)
