"""
Implementation
"""

import os as _os
import shlex as _shlex
import warnings as _warnings

import setuptools.command.test as _pytest_runner_test

class PyTest(_pytest_runner_test.test):
	user_options = [
		('junitxml=', None, "Output jUnit XML test results to specified "
			"file"),
		('extras', None, "Install (all) setuptools extras when running tests"),
		('index-url=', None, "Specify an index url from which to retrieve "
			"dependencies"),
		('allow-hosts=', None, "Whitelist of comma-separated hosts to allow "
			"when retrieving dependencies"),
		('addopts=', None, "Additional options to be passed verbatim to the "
			"pytest runner")
	]

	def initialize_options(self):
		self.junitxml = None
		self.extras = False
		self.index_url = None
		self.allow_hosts = None
		self.addopts = []

	def finalize_options(self):
		if self.addopts:
			self.addopts = _shlex.split(self.addopts)
		if self.junitxml:
			# For compatibility, allow junitxml to be provided to the plugin.
			# In the future, junitxml should be specified using addopts.
			_warnings.warn("junitxml is deprecated, use addopts to pass "
				"options to py.test", DeprecationWarning)
			self.addopts.extend(['--junitxml', self.junitxml])

	def run(self):
		"""
		Override run to ensure requirements are available in this session (but
		don't install them anywhere).
		"""
		self._build_egg_fetcher()
		if self.distribution.install_requires:
			self.distribution.fetch_build_eggs(self.distribution.install_requires)
		if self.distribution.tests_require:
			self.distribution.fetch_build_eggs(self.distribution.tests_require)
		if self.distribution.extras_require and self.extras:
			map(self.distribution.fetch_build_eggs,
				self.distribution.extras_require.values())
		if self.dry_run:
			self.announce('skipping tests (dry run)')
			return
		self.with_project_on_sys_path(self.run_tests)
		return self.result_code

	def _build_egg_fetcher(self):
		"""Build an egg fetcher that respects index_url and allow_hosts"""
		# modified from setuptools.dist:Distribution.fetch_build_egg
		from setuptools.command.easy_install import easy_install
		main_dist = self.distribution
		# construct a fake distribution to store the args for easy_install
		dist = main_dist.__class__({'script_args': ['easy_install']})
		dist.parse_config_files()
		opts = dist.get_option_dict('easy_install')
		keep = (
			'find_links', 'site_dirs', 'index_url', 'optimize',
			'site_dirs', 'allow_hosts'
		)
		for key in opts.keys():
			if key not in keep:
				del opts[key]   # don't use any other settings
		if main_dist.dependency_links:
			links = main_dist.dependency_links[:]
			if 'find_links' in opts:
				links = opts['find_links'][1].split() + links
			opts['find_links'] = ('setup', links)
		if self.allow_hosts:
			opts['allow_hosts'] = ('test', self.allow_hosts)
		if self.index_url:
			opts['index_url'] = ('test', self.index_url)
		cmd = easy_install(
			dist, args=["x"], install_dir=_os.curdir, exclude_scripts=True,
			always_copy=False, build_directory=None, editable=False,
			upgrade=False, multi_version=True, no_report = True
		)
		cmd.ensure_finalized()
		main_dist._egg_fetcher = cmd

	def run_tests(self):
		"""
		Override run_tests to invoke pytest.
		"""
		import pytest
		import sys
		# hide command-line arguments from pytest.main
		argv_saved = list(sys.argv)
		sys.argv[1:] = self.addopts
		self.result_code = pytest.main()
		sys.argv[:] = argv_saved

	@classmethod
	def install(cls, setup_params):
		"""
		Given a dictionary of keyword parameters to be passed to setup(),
		update those parameters with tests_require and cmdclass to make
		pytest available.
		"""
		reqs = setup_params.setdefault('tests_require', [])
		if not any('pytest' in req for req in reqs):
			reqs.extend(['pytest>=2.1.2'])
		setup_params.setdefault('cmdclass', {}).update(
			test=cls,
		)
		return setup_params