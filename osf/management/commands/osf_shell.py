"""Enhanced python shell.
Includes all features from django-extension's shell_plus command plus OSF-specific
niceties.

By default, sessions run in a transaction, so changes won't be commited until
you execute `commit()`.
"""
from django.db import transaction
from django.utils.termcolors import colorize
from django.db.models import Model
from django_extensions.management.commands import shell_plus
from django_extensions.management.utils import signalcommand


def header(text):
    return colorize(text, fg='green', opts=('bold', ))

def format_imported_objects(models, osf, transaction, other):
    def format_dict(d):
        return ', '.join(sorted(d.keys()))
    return """
{models_header}
{models}

{osf_header}
{osf}

{transaction_header}
{transaction}

{other_header}
{other}""".format(
        models_header=header('Models:'),
        models=format_dict(models),
        osf_header=header('OSF:'),
        osf=format_dict(osf),
        transaction_header=header('Transaction:'),
        transaction=format_dict(transaction),
        other_header=header('Django:'),
        other=format_dict(other),
    )


# kwargs will be the grouped imports, e.g. {'models': {...}, 'osf': {...}}
def make_banner(**kwargs):
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
    template = """{logo}
{greeting}
{imported_objects}
"""
    return template.format(
        logo=colorize(logo, fg='cyan'),
        greeting=colorize(greeting, opts=('bold', )),
        imported_objects=imported_objects
    )


class Command(shell_plus.Command):

    def get_osf_imports(self):
        """Return a dictionary of common OSF objects and utilities."""
        from osf.management.utils import print_sql
        from website import settings as website_settings
        from framework.auth import Auth, get_user
        from faker import Factory
        fake = Factory.create()
        return {
            'print_sql': print_sql,
            'Auth': Auth,
            'get_user': get_user,
            'website_settings': website_settings,
            'fake': fake,
        }

    # TODO: Make a cached property?
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
        def start_transaction():
            self.atomic.__enter__()
            print('New transaction opened')

        def commit():
            self.atomic.__exit__(None, None, None)
            print('Transaction committed.')
            self.atomic.__enter__()
            start_transaction()

        def rollback():
            exc_type = RuntimeError
            exc_value = exc_type('Transaction rollback')
            self.atomic.__exit__(exc_type, exc_value, None)
            print('Transaction rolled back.')
            start_transaction()

        groups = {
            'models': {},
            'other': {},
            'osf': self.get_osf_imports(),
            'transaction': {
                'start_transaction': start_transaction,
                'commit': commit,
                'rollback': rollback,
            },
        }
        # Import models and common django imports
        shell_plus_imports = shell_plus.Command.get_imported_objects(self, options)
        for name, object in shell_plus_imports.items():
            if isinstance(object, type) and issubclass(object, Model):
                groups['models'][name] = object
            else:
                groups['other'][name] = object

        return groups

    # Override shell_plus.Command
    def get_imported_objects(self, options):
        grouped_imports = self.get_grouped_imports(options)
        # Merge all the values of grouped_imports
        imported_objects = {}
        for imports in grouped_imports.values():
            imported_objects.update(imports)
        return imported_objects

    # Override shell_plus.Command
    @signalcommand
    def handle(self, *args, **options):
        self.atomic = transaction.atomic()
        options['quiet_load'] = True  # Don't show default shell_plus banner
        grouped_imports = self.get_grouped_imports(options)
        banner = make_banner(**grouped_imports)
        print(banner)
        self.atomic.__enter__()
        super(Command, self).handle(*args, **options)
