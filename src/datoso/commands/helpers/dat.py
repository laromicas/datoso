import re
import sys

from tabulate import tabulate

from datoso.database.models.dat import Dat
from datoso.helpers import Bcolors


def print_dats(args, dats, fields = None):
    """Print dats"""
    output = []
    old_fields = fields if fields else ['seed', 'name', 'status']
    fields = ['seed', 'name']
    for field in old_fields:
        if field not in fields:
            fields.append(field)
    for dat in dats:
        new_dat = { k:dat[k] for k in fields if dat.get(k) }
        if 'status' in fields:
            new_dat['status'] = dat.get('status', 'enabled') or 'enabled'
        output.append(new_dat)
    if getattr(args, 'only_names', False):
        for dat in output:
            print(f"{dat['seed']}:{dat['name']}")
        return
    print(tabulate(output, headers='keys', tablefmt='psql'))

def command_dat_name_search(args):
    from tinydb import Query
    query = Query()

    print(f'{Bcolors.WARNING}Invalid dat name, must be in format "seed:name"{Bcolors.ENDC}')
    print(f'Showing results for filter: {Bcolors.OKCYAN}name~={args.dat_name}{Bcolors.ENDC}')
    print('--------------------------------------------------------------')
    name = args.dat_name
    result = Dat.search(query.name.matches(r'^.*' + name + r'.*', flags=re.IGNORECASE))
    if args.fields:
        print_dats(args, result, fields=args.fields)
    elif args.details:
        print_dats(args, result, fields=['seed', 'name', 'modifier', 'company', 'system', 'date',
                                    'path', 'system_type', 'automerge', 'parent'])
    else:
        print_dats(args, result)

def parse_value(value):
    if value.isdigit():
        value = int(value)
    elif value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif value.lower() in ('none', 'null'):
        value = None
    return value

def command_dat_name_set(args, dat, seed, name, result):
    if '=' not in args.set:
        print(f'{Bcolors.FAIL}Invalid set command, must be in format "variable=value"{Bcolors.ENDC}')
        sys.exit(1)
    key, value = args.set.split('=') if '=' in args.set else (args.set, 'True')
    value = parse_value(value)
    dat.update({key: value}, doc_ids=[result.doc_id])
    dat.flush()
    print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} ' \
            f'{key} set to {Bcolors.OKBLUE}{value}{Bcolors.ENDC}')
    sys.exit(0)

def command_dat_name(args):
    splitted = args.dat_name.split(':')
    expected_dat_array_len = 2
    if len(splitted) != expected_dat_array_len:
        command_dat_name_search(args)
        return
    seed, name = splitted
    dat = Dat(seed=seed, name=name)
    result = dat.get_one()
    if not result:
        print(f'{Bcolors.FAIL}Dat not found{Bcolors.ENDC}')
        sys.exit(1)
    if args.set:
        command_dat_name_set(args, dat, seed, name, result)
    if args.unset:
        key = args.unset
        value = None
        dat.update({key: value}, doc_ids=[result.doc_id])
        dat.flush()
        print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} ' \
                f'{key} set to {Bcolors.OKBLUE}{value}{Bcolors.ENDC}')
        sys.exit(0)
    if args.delete:
        dat.remove(doc_ids=[result.doc_id])
        dat.flush()
        print(f'{Bcolors.OKGREEN}Dat {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} removed{Bcolors.ENDC}')
        sys.exit(0)
    if args.mark_mias:
        from datoso.mias.mia import mark_mias
        mark_mias(dat_file=result['new_file'])
        print(f'{Bcolors.OKGREEN}Set Dats {Bcolors.OKCYAN}{seed}:{name}{Bcolors.OKGREEN} marked MIAs{Bcolors.ENDC}')
        sys.exit(0)
    if args.fields:
        print(args.fields)
        print_dats(args, [result], fields=args.fields)
    elif args.details:
        print_dats(args, [result], fields=['name', 'modifier', 'company', 'system', 'seed', 'date', 'path',
                                           'system_type', 'full_name', 'automerge', 'parent'])
    else:
        print_dats(args, [result])

def helper_command_dat(args):
    """Make changes in dat config"""

    if args.dat_name:
        # Show dat by name
        command_dat_name(args)
    elif args.all:
        # Show all dats
        print_dats(args, Dat.all())

    elif args.find:
        # Find dats TODO: finish
        print(f'Showing results for filter: {Bcolors.OKCYAN}{args.find}{Bcolors.ENDC}')
        print('--------------------------------------------------------------')
        name, value = args.find.split('=')
        from tinydb import where
        result = Dat.search(where(name) == value)
        print_dats(args, result)
