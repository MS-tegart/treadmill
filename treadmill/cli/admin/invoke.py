"""Implementation of treadmill-admin CLI plugin.
"""

import pwd
import importlib
import os
import pkgutil

import decorator
import click

import jsonschema
import yaml

from treadmill import authz as authz_mod
from treadmill import cli
from treadmill import context


class Context(object):
    """CLI context."""

    def __init__(self):
        self.authorizer = authz_mod.NullAuthorizer()

    def authorize(self, resource, action, args, kwargs):
        """Invoke internal authorizer."""
        self.authorizer.authorize(resource, action, args, kwargs)


def list_resource_types(api):
    """List available resource types."""
    apimod = importlib.import_module(api)
    return sorted([
        modulename for _loader, modulename, _ispkg
        in pkgutil.iter_modules(apimod.__path__)
    ])


def _import_resource_mod(resource_type, debug=False):
    """Safely import module for given resource type."""
    # Ignore private variables.
    if resource_type.startswith('_'):
        return None

    try:
        return importlib.import_module('treadmill.api.' + resource_type)
    except ImportError:
        if not debug:
            raise click.BadParameter(resource_type)
        else:
            raise


def make_command(parent, name, func):
    """Make a command using reflection on the function."""
    # Disable "Too many branches" warning.
    #
    # pylint: disable=R0912
    argspec = decorator.getargspec(func)
    args = list(argspec.args)
    defaults = argspec.defaults
    if defaults is None:
        defaults = []
    else:
        defaults = list(defaults)

    @parent.command(name=name, help=func.__doc__)
    def command(*args, **kwargs):
        """Constructs a command handler."""
        try:
            if 'rsrc' in kwargs:
                with open(kwargs['rsrc'], 'rb') as fd:
                    kwargs['rsrc'] = yaml.load(fd.read())

            formatter = cli.make_formatter(None)
            cli.out(formatter(func(*args, **kwargs)))

        except jsonschema.exceptions.ValidationError as input_err:
            click.echo(input_err, err=True)
        except jsonschema.exceptions.RefResolutionError as res_error:
            click.echo(res_error, err=True)
        except authz_mod.AuthorizationError as auth_err:
            click.echo('Not authorized.', err=True)
            click.echo(auth_err, err=True)
        except TypeError as type_err:
            click.echo(type_err, err=True)

    while defaults:
        arg = args.pop()
        defarg = defaults.pop()
        if defarg is not None:
            argtype = type(defarg)
        else:
            argtype = str

        if defarg == ():
            # redefinition of the type from tuple to list.
            argtype = cli.LIST  # pylint: disable=R0204
            defarg = None

        click.option('--' + arg, default=defarg, type=argtype)(command)

    if not args:
        return

    arg = args.pop(0)
    click.argument(arg)(command)

    while args:
        if len(args) == 1:
            arg = args.pop(0)
            click.argument(
                arg,
                type=click.Path(exists=True, readable=True)
            )(command)
        else:
            arg = args.pop(0)
            click.argument(arg)(command)

    if args:
        raise click.UsageError('Non-standard API: %s, %r' % (name, argspec))


def make_resource_group(ctx, parent, resource_type, api=None):
    """Make click group for a resource type."""
    if api is None:
        mod = _import_resource_mod(resource_type)
        if not mod:
            return

        try:
            api = getattr(mod, 'init')(ctx)
        except AttributeError:
            return

    @parent.group(name=resource_type, help=api.__doc__)
    def _rsrc_group():
        """Creates a CLI group for the given resource type."""
        pass

    for verb in dir(api):
        if verb.startswith('__'):
            continue

        func = getattr(api, verb)
        if hasattr(func, '__call__'):
            make_command(_rsrc_group, verb, func)
        elif hasattr(func, '__init__'):
            make_resource_group(ctx, _rsrc_group, verb, func)


def init():
    """Constructs parent level CLI group."""

    ctx = Context()

    @click.group()
    @click.option('--authz', required=False)
    @click.option('--cell', required=True,
                  envvar='TREADMILL_CELL',
                  callback=cli.handle_context_opt,
                  expose_value=False)
    def invoke(authz):
        """Directly invoke Treadmill API without REST."""
        if authz is not None:
            ctx.authorizer = authz_mod.ClientAuthorizer(
                lambda: pwd.getpwuid(os.getuid()).pw_name,
                authz
            )
        else:
            ctx.authorizer = authz_mod.NullAuthorizer()

        if cli.OUTPUT_FORMAT == 'pretty':
            raise click.BadParameter('must use --outfmt [json|yaml]')

    for resource in list_resource_types('treadmill.api'):
        # TODO: for now, catch the ContextError as endpoint.py and state.py are
        # calling context.GLOBAL.zk.conn, which fails, as cell is not set yet
        try:
            make_resource_group(ctx, invoke, resource)
        except context.ContextError:
            pass

    return invoke
