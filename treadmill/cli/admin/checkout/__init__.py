"""Treadmill cell checkout."""

import collections
import pkgutil
import sys
import unittest

import click
import HtmlTestRunner

from treadmill import cli


__path__ = pkgutil.extend_path(__path__, __name__)


def init():
    """Top level command handler."""

    @click.group(cls=cli.make_multi_command(__name__,
                                            chain=True,
                                            invoke_without_command=True))
    @click.option('--cell', required=True,
                  envvar='TREADMILL_CELL',
                  callback=cli.handle_context_opt,
                  expose_value=False)
    @click.option('--verbose', is_flag=True, default=False)
    @click.option('--html', is_flag=True, default=False)
    def run(verbose, html):
        """Run interactive checkout."""
        del verbose
        del html

    @run.resultcallback()
    def run_tests(tests, verbose, html):
        """Run interactive checkout."""
        verbosity = 1
        if verbose:
            verbosity = 2

        suite = unittest.TestSuite()
        loader = unittest.TestLoader()

        for factory in tests:
            tests = factory()
            if isinstance(tests, collections.Iterable):
                for test in tests:
                    suite.addTests(loader.loadTestsFromTestCase(test))
            else:
                suite.addTests(loader.loadTestsFromTestCase(tests))

        if html:
            runner = HtmlTestRunner.HtmlTestRunner(
                stream=sys.stdout,
                title='Treadmill cell checkout',
                description='Treamdill cell checkout tests'
            )
        else:
            runner = unittest.TextTestRunner(verbosity=verbosity)

        runner.run(suite)

    # commands.init(run)

    del run_tests

    return run
