#!/usr/bin/env python
"""
Test suite for the dyPolyChord package.

Extra tests which check exact results produced using random seeding are
included, but are skipped unless pypolychord is installed. These also require
mpi4py if you have installed PolyChord with MPI.

Note that pypolychord was called PyPolyChord before PolyChord v1.15;
if pypolychord cannot be imported then we try importing PyPolyChord
instead for backwards compatibility with the old module name.
"""
import os
import copy
import shutil
import unittest
import functools
import warnings
import scipy.special
import numpy as np
import numpy.testing
import nestcheck.estimators as e
import nestcheck.dummy_data
import nestcheck.write_polychord_output
import nestcheck.data_processing
import dyPolyChord.python_likelihoods as likelihoods
import dyPolyChord.python_priors as priors
import dyPolyChord.output_processing
import dyPolyChord.polychord_utils
import dyPolyChord.run_dynamic_ns
import dyPolyChord
try:
    # pylint: disable=unused-import,ungrouped-imports
    # Only do pypolychord_utils tests if pypolychord is installed
    try:
        import pypolychord
    except ImportError:
        # See if pypolychord is installed under its old name
        import PyPolyChord as pypolychord
    import dyPolyChord.pypolychord_utils
    PYPOLYCHORD_AVAIL = True
except ImportError:
    PYPOLYCHORD_AVAIL = False
    warnings.warn(
        ('I can\'t import pypolychord (I also tried importing it using its '
         'old name "PyPolyChord"). I am therefore skipping the tests which '
         'need it. pypolychord is not needed for compiled C++ and Fortran '
         'likelihoods, so you can ignore this warning. However, you will need '
         'to install pypolychord to run Python likelihoods.'),
        UserWarning)
if PYPOLYCHORD_AVAIL:
    try:
        # If PolyChord is installed with MPI, we need to initialise mpi4py in order
        # to run it multiple times from within the same python process without
        # having an error.
        # pylint: disable=unused-import
        from mpi4py import MPI  # Initialize MPI
    except ImportError:
        warnings.warn(
            ('I can\'t import mpi4py. This is only needed by '
             'dyPolyChord when PolyChord is installed with MPI. If this '
             'is the case, the tests will fail and you should install mpi4py. '
             'If your PolyChord install does not use MPI, you can ignore/'
             'comment out/filter this warning.'),
            UserWarning)


# Define a directory to output files produced by tests (this will be deleted
# when the tests finish).
TEST_CACHE_DIR = 'temp_test_data_to_delete'


def setUpModule():
    """Before running the test suite, check that TEST_CACHE_DIR does not
    already exist - as the tests will delete it."""
    if os.path.exists(TEST_CACHE_DIR):
        warnings.warn((
            'Directory ' + TEST_CACHE_DIR + ' exists! Tests use this '
            'directory to check caching and delete it afterwards, so its '
            'path should be left empty.'), UserWarning)
        shutil.rmtree(TEST_CACHE_DIR)


@unittest.skipIf(not PYPOLYCHORD_AVAIL, 'pypolychord not installed.')
class TestRunDyPolyChordNumers(unittest.TestCase):

    """Tests for run_dypolychord which use pypolychord and check numerical
    outputs by setting random seed."""

    def setUp(self):
        """Make a directory for saving test results."""
        try:
            os.makedirs(TEST_CACHE_DIR)
        except FileExistsError:
            pass
        self.ninit = 40
        ndim = 4
        self.run_func = dyPolyChord.pypolychord_utils.RunPyPolyChord(
            likelihoods.Gaussian(sigma=1), priors.Uniform(-10, 10), ndim=ndim)
        self.random_seed_msg = (
            'First dead point logl {0} != {1}. '
            'This indicates that your PolyChord install\'s random number '
            'generator is different to the one used to calculate the expected '
            'results, so I will skip tests of exact numerical values. If all '
            'the other tests pass then everything should work ok.')
        self.settings = {
            'do_clustering': True,
            'posteriors': False,
            'equals': False,
            'write_dead': True,
            'read_resume': False,
            'write_resume': False,
            'write_stats': True,
            'write_prior': False,
            'write_live': False,
            'num_repeats': 10,
            'feedback': -1,
            'cluster_posteriors': False,
            # Set precision_criterion to a relatively high value (i.e.
            # precision) to PolyChord "non-deterministic likelihood" problems.
            # These occur due in the low dimension and low and nlive
            # cases we use for fast testing as runs sometimes get very close
            # to the peak where the likelihood becomes approximately constant,
            # and at this point PolyChord gets stuck.
            'precision_criterion': 0.1,
            'seed': 1,
            'max_ndead': -1,
            'base_dir': TEST_CACHE_DIR,
            'file_root': 'test_run',
            'nlive': 100,  # used for nlive_const
            'nlives': {}}

    def tearDown(self):
        """Remove any caches saved by the tests."""
        try:
            shutil.rmtree(TEST_CACHE_DIR)
        except FileNotFoundError:
            pass

    def test_dynamic_evidence(self):
        """Test numerical results for nested sampling with dynamic_goal=0."""
        dynamic_goal = 0
        dyPolyChord.run_dypolychord(
            self.run_func, dynamic_goal, self.settings,
            init_step=self.ninit, ninit=self.ninit)
        run = nestcheck.data_processing.process_polychord_run(
            self.settings['file_root'], self.settings['base_dir'])
        first_logl = -158.773632799691
        if not np.isclose(run['logl'][0], first_logl):
            warnings.warn(
                self.random_seed_msg.format(run['logl'][0], first_logl),
                UserWarning)
        else:
            self.assertEqual(e.count_samples(run), 1169)
            self.assertAlmostEqual(e.param_mean(run), 0.026487985350451874,
                                   places=12)

    def test_dynamic_both_evidence_and_param(self):
        """Test numerical results for nested sampling with
        dynamic_goal=0.25."""
        dynamic_goal = 0.25
        dyPolyChord.run_dypolychord(
            self.run_func, dynamic_goal, self.settings,
            init_step=self.ninit, ninit=self.ninit)
        run = nestcheck.data_processing.process_polychord_run(
            self.settings['file_root'], self.settings['base_dir'])
        first_logl = -165.502617578541
        if not np.isclose(run['logl'][0], first_logl):
            warnings.warn(
                self.random_seed_msg.format(run['logl'][0], first_logl),
                UserWarning)
        else:
            self.assertEqual(e.count_samples(run), 1093)
            self.assertAlmostEqual(e.param_mean(run), -0.0021307716191374263,
                                   places=12)

    def test_dynamic_param(self):
        """Test numerical results for nested sampling with dynamic_goal=1."""
        dynamic_goal = 1
        dyPolyChord.run_dypolychord(
            self.run_func, dynamic_goal, self.settings,
            init_step=self.ninit, ninit=self.ninit)
        run = nestcheck.data_processing.process_polychord_run(
            self.settings['file_root'], self.settings['base_dir'])
        first_logl = -137.231721859574
        if not np.isclose(run['logl'][0], first_logl):
            warnings.warn(
                self.random_seed_msg.format(run['logl'][0], first_logl),
                UserWarning)
        else:
            self.assertAlmostEqual(e.param_mean(run), -0.05323120028149568,
                                   places=12)


class TestRunDynamicNS(unittest.TestCase):

    """Tests for the run_dynamic_ns.py module."""

    def setUp(self):
        """Set up function for make dummy PolyChord data, a directory for
        saving test results and some settings."""
        try:
            os.makedirs(TEST_CACHE_DIR)
        except FileExistsError:
            pass
        self.random_seed_msg = (
            'This test is not affected by dyPolyChord, so if it fails '
            'your numpy random seed number generator is probably different '
            'to the one used to set the expected values.')
        self.ninit = 2
        self.nlive_const = 4
        self.run_func = functools.partial(
            dummy_run_func, ndim=2, ndead_term=10, seed=1, logl_range=10)
        self.settings = {'base_dir': TEST_CACHE_DIR,
                         'file_root': 'test_run',
                         'seed': 1,
                         'max_ndead': -1,
                         'posteriors': True}

    def tearDown(self):
        """Remove any caches saved by the tests."""
        try:
            shutil.rmtree(TEST_CACHE_DIR)
        except IOError:
            pass

    def test_run_dypolychord_unexpected_kwargs(self):
        """Check appropriate error is raised when an unexpected keyword
        argument is given."""
        self.assertRaises(
            TypeError, dyPolyChord.run_dypolychord,
            lambda x: None, 1, {}, unexpected=1)

    def test_dynamic_evidence(self):
        """Check run_dypolychord targeting evidence. This uses dummy
        PolyChord-format data."""
        dynamic_goal = 0
        self.settings['max_ndead'] = 24
        dyPolyChord.run_dypolychord(
            self.run_func, dynamic_goal, self.settings,
            init_step=self.ninit, ninit=self.ninit,
            nlive_const=self.nlive_const, stats_means_errs=False)
        # Check the mean value using the posteriors file (its hard to make a
        # dummy run_func which is realistic enough to not fail checks if we try
        # loading the output normally with
        # nesthcheck.data_processing.process_polychord_run).
        posteriors = np.loadtxt(os.path.join(
            self.settings['base_dir'], self.settings['file_root'] + '.txt'))
        # posteriors have columns: weight / max weight, -2*logl, [params]
        p1_mean = (np.sum(posteriors[:, 2] * posteriors[:, 0])
                   / np.sum(posteriors[:, 0]))
        self.assertAlmostEqual(p1_mean, 0.6509612992491138, places=12)

    def test_dynamic_param(self):
        """Check run_dypolychord targeting evidence. This uses dummy
        PolyChord-format data."""
        dynamic_goal = 1
        dyPolyChord.run_dypolychord(
            self.run_func, dynamic_goal, self.settings,
            init_step=self.ninit, ninit=self.ninit,
            nlive_const=self.nlive_const, stats_means_errs=False)
        # Check the mean value using the posteriors file (its hard to make a
        # dummy run_func which is realistic enough to not fail checks if we try
        # loading the output normally with
        # nesthcheck.data_processing.process_polychord_run).
        posteriors = np.loadtxt(os.path.join(
            self.settings['base_dir'], self.settings['file_root'] + '.txt'))
        # posteriors have columns: weight / max weight, -2*logl, [params]
        p1_mean = (np.sum(posteriors[:, 2] * posteriors[:, 0])
                   / np.sum(posteriors[:, 0]))
        self.assertAlmostEqual(p1_mean, 0.614126384660822, places=12)

    def test_comm(self):
        """Test run_dyPolyChord's comm argument, which is used for running
        python likelihoods using MPI parallelisation with mpi4py.

        This should raise a warning due to running with seed > 0 and
        comm.Get_size() > 1 to remind users that seeding is not reliable when
        multiple MPI processes are used."""
        dynamic_goal = 1
        with warnings.catch_warnings(record=True) as war:
            warnings.simplefilter("always")
            self.assertRaises(
                AssertionError, dyPolyChord.run_dypolychord,
                self.run_func, dynamic_goal, self.settings,
                init_step=self.ninit, ninit=self.ninit,
                nlive_const=self.nlive_const, comm=DummyMPIComm(0))
            self.assertEqual(len(war), 1)

    def test_check_settings(self):
        """Make sure settings are checked ok, including issuing warning if a
        setting with a mandatory value is given a different value."""
        settings = {'read_resume': True, 'equals': True, 'posteriors': False}
        with warnings.catch_warnings(record=True) as war:
            warnings.simplefilter("always")
            dyPolyChord.run_dynamic_ns.check_settings(settings)
            self.assertEqual(len(war), 1)


class TestNliveAllocation(unittest.TestCase):

    """Tests for the nlive_allocation.py module."""

    def test_allocate(self):
        """Check the allocate function for computing where to put additional
        samples."""
        dynamic_goal = 1
        run = nestcheck.dummy_data.get_dummy_run(2, 10, ndim=2, seed=0)
        with warnings.catch_warnings(record=True) as war:
            warnings.simplefilter("always")
            dyn_info = dyPolyChord.nlive_allocation.allocate(
                run, 40, dynamic_goal, smoothing_filter=None)
            self.assertEqual(len(war), 1)
        numpy.testing.assert_array_equal(
            dyn_info['init_nlive_allocation'],
            dyn_info['init_nlive_allocation_unsmoothed'])
        # Check no points remaining error
        self.assertRaises(
            AssertionError, dyPolyChord.nlive_allocation.allocate,
            run, 1, dynamic_goal)

    def test_dyn_nlive_array_warning(self):
        """Check handling of case where nlive smoothing introduces unwanted
        convexity for dynamic_goal=0."""
        dynamic_goal = 0
        run = nestcheck.dummy_data.get_dummy_run(2, 10, ndim=2, seed=0)
        smoothing = (lambda x: (x + 100 * np.asarray(list(range(x.shape[0])))))
        with warnings.catch_warnings(record=True) as war:
            warnings.simplefilter("always")
            dyn_info = dyPolyChord.nlive_allocation.allocate(
                run, 40, dynamic_goal, smoothing_filter=smoothing)
            self.assertEqual(len(war), 1)
        numpy.testing.assert_array_equal(
            dyn_info['init_nlive_allocation'],
            dyn_info['init_nlive_allocation_unsmoothed'])

    def test_sample_importance(self):
        """Check sample importance provides expected results."""
        run = nestcheck.dummy_data.get_dummy_thread(
            4, ndim=2, seed=0, logl_range=1)
        imp = dyPolyChord.nlive_allocation.sample_importance(run, 0.5)
        self.assertEqual(run['logl'].shape, imp.shape)
        numpy.testing.assert_allclose(
            np.asarray([0.66121679, 0.23896365, 0.08104094, 0.01877862]),
            imp)


class TestOutputProcessing(unittest.TestCase):

    """Tests for the output_processing.py module."""

    def test_settings_root(self):
        """Check standard settings root string."""
        root = dyPolyChord.output_processing.settings_root(
            'gaussian', 'uniform', 2, prior_scale=1, dynamic_goal=1,
            nlive_const=1, ninit=1, nrepeats=1, init_step=1)
        self.assertEqual(
            'gaussian_uniform_1_dg1_1init_1is_2d_1nlive_1nrepeats', root)

    def test_settings_root_unexpected_kwarg(self):
        """Check appropriate error is raised when an unexpected keyword
        argument is given."""
        self.assertRaises(
            TypeError, dyPolyChord.output_processing.settings_root,
            'gaussian', 'uniform', 2, prior_scale=1, dynamic_goal=1,
            nlive_const=1, ninit=1, nrepeats=1, init_step=1,
            unexpected=1)

    def test_process_dypolychord_run_unexpected_kwarg(self):
        """Check appropriate error is raised when an unexpected keyword
        argument is given."""
        self.assertRaises(
            TypeError, dyPolyChord.output_processing.process_dypolychord_run,
            'file_root', 'base_dir', dynamic_goal=1, unexpected=1)

    def test_combine_resumed_dyn_run(self):
        """Test combining resumed dynamic and initial runs and removing
        duplicate points using dummy ns runs.
        """
        init = {'logl': np.asarray([0, 1, 2, 3]),
                'thread_labels': np.asarray([0, 1, 0, 1])}
        dyn = {'logl': np.asarray([0, 1, 2, 4, 5, 6]),
               'thread_labels': np.asarray([0, 1, 0, 1, 0, 1])}
        for run in [init, dyn]:
            run['theta'] = np.random.random((run['logl'].shape[0], 2))
            run['nlive_array'] = np.zeros(run['logl'].shape[0]) + 2
            run['nlive_array'][-1] = 1
            run['thread_min_max'] = np.asarray(
                [[-np.inf, run['logl'][-2]], [-np.inf, run['logl'][-1]]])
        with warnings.catch_warnings(record=True) as war:
            warnings.simplefilter("always")
            # when live points at resume are not present in both init and dyn,
            # a warning should be given
            dyPolyChord.output_processing.combine_resumed_dyn_run(
                init.copy(), dyn.copy(), 2)
            self.assertEqual(len(war), 1)
        comb = dyPolyChord.output_processing.combine_resumed_dyn_run(
            init, dyn, 1)
        self.assertEqual(set(comb.keys()),
                         {'nlive_array', 'theta', 'logl', 'thread_labels',
                          'thread_min_max'})
        numpy.testing.assert_array_equal(
            comb['thread_labels'], np.asarray([0, 1, 0, 2, 1, 0, 1]))
        numpy.testing.assert_array_equal(
            comb['logl'], np.asarray([0., 1., 2., 3., 4., 5., 6.]))
        numpy.testing.assert_array_equal(
            comb['nlive_array'], np.asarray([2., 2., 3., 3., 2., 2., 1.]))


class TestPolyChordUtils(unittest.TestCase):

    """Tests for the polychord_utils.py module."""

    def setUp(self):
        try:
            os.makedirs(TEST_CACHE_DIR)
        except FileExistsError:
            pass

    def tearDown(self):
        """Remove any caches saved by the tests."""
        try:
            shutil.rmtree(TEST_CACHE_DIR)
        except IOError:
            pass

    def test_format_settings(self):
        """Check putting settings dictionary values into the format needed for
        PolyChord .ini files."""
        self.assertEqual(
            'T', dyPolyChord.polychord_utils.format_setting(True))
        self.assertEqual(
            'F', dyPolyChord.polychord_utils.format_setting(False))
        self.assertEqual(
            '1', dyPolyChord.polychord_utils.format_setting(1))
        self.assertEqual(
            '1 2', dyPolyChord.polychord_utils.format_setting([1, 2]))

    def test_get_prior_block_str(self):
        """Check generating prior blocks in the format needed for PolyChord
        .ini files."""
        name = 'uniform'
        prior_params = [1, 2]
        expected = ('P : p{0} | \\theta_{{{0}}} | {1} | {2} | {3} |'
                    .format(1, 1, name, 1))
        expected += dyPolyChord.polychord_utils.format_setting(prior_params)
        expected += '\n'
        self.assertEqual(dyPolyChord.polychord_utils.get_prior_block_str(
            name, prior_params, 1, speed=1, block=1), expected)

    def test_python_prior_to_str(self):
        """Check functions for mapping Python prior objects to ini file
        strings."""
        nparam = 3
        prior_params = [1, 2, -3]
        prior_str = dyPolyChord.polychord_utils.get_prior_block_str(
            'adaptive_sorted_uniform', prior_params[:2], nparam)
        prior_obj = dyPolyChord.python_priors.Uniform(
            *prior_params[:2], adaptive=True, sort=True)
        self.assertEqual(
            dyPolyChord.polychord_utils.python_prior_to_str(
                prior_obj, nparam=nparam),
            prior_str)
        # Now check from block prior
        block_obj = dyPolyChord.python_priors.BlockPrior(
            [prior_obj], [nparam])
        self.assertEqual(
            dyPolyChord.polychord_utils.python_block_prior_to_str(
                block_obj), prior_str)
        # Finally, lets check the other types of prior
        # Power uniform
        prior_str = dyPolyChord.polychord_utils.get_prior_block_str(
            'power_uniform', prior_params, nparam)
        prior_obj = dyPolyChord.python_priors.PowerUniform(
            *prior_params)
        self.assertEqual(
            dyPolyChord.polychord_utils.python_prior_to_str(
                prior_obj, nparam=nparam), prior_str)
        # Exponential
        prior_str = dyPolyChord.polychord_utils.get_prior_block_str(
            'exponential', prior_params[:1], nparam)
        prior_obj = dyPolyChord.python_priors.Exponential(
            *prior_params[:1])
        self.assertEqual(
            dyPolyChord.polychord_utils.python_prior_to_str(
                prior_obj, nparam=nparam), prior_str)
        # (half) Gaussian
        mu = 0.5
        prior_str = dyPolyChord.polychord_utils.get_prior_block_str(
            'half_gaussian', [mu, prior_params[0]], nparam)
        prior_obj = dyPolyChord.python_priors.Gaussian(
            *prior_params[:1], half=True, mu=mu)
        self.assertEqual(
            dyPolyChord.polychord_utils.python_prior_to_str(
                prior_obj, nparam=nparam), prior_str)


    def test_get_prior_block_unexpected_kwargs(self):
        """Check appropriate error is raised when an unexpected keyword
        argument is given."""
        self.assertRaises(
            TypeError, dyPolyChord.polychord_utils.get_prior_block_str,
            'param_name', (1, 2), 2, unexpected=1)

    def test_write_ini(self):
        """Check writing a PolyChord .ini file from a dictionary of
        settings."""
        settings = {'nlive': 50, 'nlives': {-20.0: 100, -10.0: 200}}
        prior_str = 'prior_block\n'
        derived_str = 'derived'
        run_obj = dyPolyChord.polychord_utils.RunCompiledPolyChord(
            ':', prior_str, derived_str=derived_str)
        lines = run_obj.ini_string(settings).splitlines()
        self.assertEqual(lines[-2], prior_str.replace('\n', ''))
        self.assertEqual(lines[-1], derived_str)
        # Use sorted as ini lines written from dict.items() so order not
        # guarenteed.
        self.assertEqual(sorted(lines[:3]),
                         ['loglikes = -20.0 -10.0',
                          'nlive = 50',
                          'nlives = 100 200'])

    def test_compiled_run_func(self):
        """
        Check function for running a compiled PolyChord likelihood from
        within python (via os.system).

        In place of an executable we just use a dummy file made with np.savetxt
        as RunCompiledPolyChord checks if the file exists. We use the mpi_str
        argument to comment out the command so nothing actually runs.
        """
        executable_path = os.path.join(TEST_CACHE_DIR, 'dummy_ex')
        print(executable_path, type(executable_path))
        np.savetxt(executable_path, np.zeros(10))
        func = dyPolyChord.polychord_utils.RunCompiledPolyChord(
            executable_path, 'this is a dummy prior block string', mpi_str='#',
            config_str='this is a dummy config string')
        self.assertEqual(set(func.__dict__.keys()),
                         {'derived_str', 'executable_path', 'prior_str',
                          'mpi_str', 'config_str'})
        func({'base_dir': TEST_CACHE_DIR, 'file_root': 'temp'})


@unittest.skipIf(not PYPOLYCHORD_AVAIL, 'pypolychord not installed.')
class TestPyPolyChordUtils(unittest.TestCase):

    """
    Tests for the pypolychord_utils.py module.

    These are skipped if pypolychord is not installed as it is not needed for
    compiled likelihoods.
    """

    def test_python_run_func(self):
        """Check functions for running PolyChord via the pypolychord wrapper
        (as opposed to with a compiled likelihood) in the form needed for
        dynamic nested sampling."""
        try:
            os.makedirs(TEST_CACHE_DIR)
        except FileExistsError:
            pass
        func = dyPolyChord.pypolychord_utils.RunPyPolyChord(
            likelihoods.Gaussian(), priors.Uniform(), 2)
        self.assertEqual(set(func.__dict__.keys()),
                         {'nderived', 'ndim', 'likelihood', 'prior'})
        func({'base_dir': TEST_CACHE_DIR, 'file_root': 'temp', 'nlive': 5,
              'max_ndead': 5, 'feedback': -1})
        shutil.rmtree(TEST_CACHE_DIR)

    def test_comm(self):
        """
        Test python_run_func's comm argument (used for MPI) has the expected
        behavior.
        """
        run_func = dyPolyChord.pypolychord_utils.RunPyPolyChord(1, 2, 3)
        self.assertRaises(
            AssertionError, run_func, {}, comm=DummyMPIComm(0))
        self.assertRaises(
            AssertionError, run_func, {}, comm=DummyMPIComm(1))


class TestPythonPriors(unittest.TestCase):

    """Tests for the python_priors.py module."""

    @staticmethod
    def test_base_prior():
        """Check uniform prior."""
        state = np.random.get_state()
        np.random.seed(0)
        cube = np.random.random(5)
        # Check without sorting or adaptive
        numpy.testing.assert_allclose(
            cube, dyPolyChord.python_priors.BasePrior()(cube))
        # Check with sorting
        numpy.testing.assert_allclose(
            dyPolyChord.python_priors.forced_identifiability(cube),
            dyPolyChord.python_priors.BasePrior(sort=True)(cube))
        np.random.set_state(state)
        # Check adaptive
        expected = copy.deepcopy(cube)
        expected[0] = 0.5 + (expected[0] * (cube.shape[0] - 1))
        nfunc = int(np.round(expected[0]))
        expected[1:1 + nfunc] = (
            dyPolyChord.python_priors.forced_identifiability(
                expected[1:1 + nfunc]))
        numpy.testing.assert_allclose(
            dyPolyChord.python_priors.BasePrior(
                adaptive=True, sort=True)(cube),
            expected)
        # Check adaptive nan handling
        cube[0] = np.nan
        numpy.testing.assert_allclose(
            np.full(cube.shape, np.nan),
            dyPolyChord.python_priors.Uniform(adaptive=True, sort=True)(cube))

    @staticmethod
    def test_uniform():
        """Check uniform prior."""
        prior_scale = 5
        hypercube = np.random.random(5)
        theta_prior = dyPolyChord.python_priors.Uniform(
            -prior_scale, prior_scale)(hypercube)
        theta_check = (hypercube * 2 * prior_scale) - prior_scale
        numpy.testing.assert_allclose(theta_prior, theta_check)

    @staticmethod
    def test_power_uniform():
        """Check prior for some power of theta uniformly distributed"""
        cube = np.random.random(10)
        for power in [-2, 3]:
            maximum = 20
            minimum = 0.1
            theta = dyPolyChord.python_priors.PowerUniform(
                minimum, maximum, power=power)(cube)
            # Check this vs doing a uniform prior and transforming
            # Note if power < 0, the high to low order of X is inverted
            umin = min(minimum ** (1.0 / power), maximum ** (1.0 / power))
            umax = max(minimum ** (1.0 / power), maximum ** (1.0 / power))
            test_prior = dyPolyChord.python_priors.Uniform(umin, umax)
            if power < 0:
                theta_check = test_prior(1 - cube) ** power
            else:
                theta_check = test_prior(cube) ** power
            numpy.testing.assert_allclose(theta, theta_check)


    @staticmethod
    def test_gaussian():
        """Check spherically symmetric Gaussian prior centred on the origin."""
        prior_scale = 5
        hypercube = np.random.random(5)
        theta_prior = dyPolyChord.python_priors.Gaussian(
            prior_scale)(hypercube)
        theta_check = (scipy.special.erfinv(hypercube * 2 - 1) *
                       prior_scale * np.sqrt(2))
        numpy.testing.assert_allclose(theta_prior, theta_check)
        # With half=True
        theta_prior = dyPolyChord.python_priors.Gaussian(
            prior_scale, half=True)(hypercube)
        theta_check = (scipy.special.erfinv(hypercube) *
                       prior_scale * np.sqrt(2))
        numpy.testing.assert_allclose(theta_prior, theta_check)

    @staticmethod
    def test_exponential_prior():
        """Check the exponential prior."""
        prior_scale = 5
        hypercube = np.random.random(5)
        theta_prior = dyPolyChord.python_priors.Exponential(
            prior_scale)(hypercube)
        theta_check = -np.log(1 - hypercube) / prior_scale
        numpy.testing.assert_allclose(theta_prior, theta_check)

    @staticmethod
    def test_block_prior():
        """Check the block prior."""
        prior_blocks = [dyPolyChord.python_priors.Uniform(0, 1),
                        dyPolyChord.python_priors.Uniform(1, 2)]
        block_sizes = [2, 3]
        hypercube = np.random.random(sum(block_sizes))
        theta_prior = dyPolyChord.python_priors.BlockPrior(
            prior_blocks, block_sizes)(hypercube)
        theta_check = copy.deepcopy(hypercube)
        theta_check[block_sizes[0]:] += 1
        numpy.testing.assert_allclose(theta_prior, theta_check)


    @staticmethod
    def test_forced_identifiability():
        """Check the forced identifiability (forced ordering) transform.
        Note that the PolyChord paper contains a typo in the formulae."""
        n = 5
        hypercube = np.random.random(n)
        theta_func = dyPolyChord.python_priors.forced_identifiability(
            hypercube)

        def forced_ident_transform(x):
            """pypolychord version of the forced identifiability transform.
            (gives correct value)."""
            n = len(x)
            theta = numpy.zeros(n)
            theta[n - 1] = x[n - 1] ** (1. / n)
            for i in range(n - 2, -1, -1):
                theta[i] = x[i] ** (1. / (i + 1)) * theta[i + 1]
            return theta

        theta_check = forced_ident_transform(hypercube)
        numpy.testing.assert_allclose(theta_func, theta_check)


class TestPythonLikelihoods(unittest.TestCase):

    """Tests for the python_likelihoods.py module."""

    def test_gaussian(self):
        """Check the Gaussian likelihood."""
        sigma = 1
        dim = 5
        theta = np.random.random(dim)
        logl_expected = -(np.sum(theta ** 2) / (2 * sigma ** 2))
        logl_expected -= np.log(2 * np.pi * sigma ** 2) * (dim / 2.0)
        logl, phi = likelihoods.Gaussian(sigma=sigma)(theta)
        self.assertAlmostEqual(logl, logl_expected, places=12)
        self.assertIsInstance(phi, list)
        self.assertEqual(len(phi), 0)
        # Check matches sum of individal logls
        sep_logls = [likelihoods.log_gaussian_pdf(th, sigma=sigma)
                     for th in theta]
        self.assertAlmostEqual(sum(sep_logls), logl)

    def test_gaussian_shell(self):
        """Check the Gaussian shell likelihood."""
        dim = 5
        sigma = 1
        rshell = 2
        theta = np.random.random(dim)
        r = np.sum(theta ** 2) ** 0.5
        logl, phi = likelihoods.GaussianShell(
            sigma=sigma, rshell=rshell)(theta)
        self.assertAlmostEqual(
            logl, -((r - rshell) ** 2) / (2 * (sigma ** 2)), places=12)
        self.assertIsInstance(phi, list)
        self.assertEqual(len(phi), 0)

    def test_gaussian_mix(self):
        """Check the Gaussian mixture model likelihood."""
        dim = 5
        theta = np.random.random(dim)
        _, phi = likelihoods.GaussianMix()(theta)
        self.assertIsInstance(phi, list)
        self.assertEqual(len(phi), 0)

    def test_loggamma_mix(self):
        """Check the loggamma mixture model likelihood."""
        dim = 6
        theta = np.random.random(dim)
        _, phi = likelihoods.LogGammaMix()(theta)
        self.assertIsInstance(phi, list)
        self.assertEqual(len(phi), 0)

    def test_rastrigin(self):
        """Check the Rastrigin ("bunch of grapes") likelihood."""
        dim = 2
        theta = np.zeros(dim)
        logl, phi = likelihoods.Rastrigin()(theta)
        self.assertEqual(logl, 0)
        self.assertIsInstance(phi, list)
        self.assertEqual(len(phi), 0)

    def test_rosenbrock(self):
        """Check the Rosenbrock ("banana") likelihood."""
        dim = 2
        theta = np.zeros(dim)
        logl, phi = likelihoods.Rosenbrock()(theta)
        self.assertAlmostEqual(logl, -1, places=12)
        self.assertIsInstance(phi, list)
        self.assertEqual(len(phi), 0)


# Helper functions
# ----------------


def dummy_run_func(settings, **kwargs):
    """
    Produces dummy PolyChord output files for use in testing.
    """
    ndim = kwargs.pop('ndim', 2)
    ndead_term = kwargs.pop('ndead_term', 10)
    seed = kwargs.pop('seed', 1)
    logl_range = kwargs.pop('logl_range', 10)
    write_stats = kwargs.pop('write_stats', True)
    kwargs.pop('comm', None)
    if kwargs:
        raise TypeError('Unexpected **kwargs: {0}'.format(kwargs))
    nthread = settings['nlive']
    if settings['max_ndead'] <= 0:
        ndead = ndead_term
    else:
        ndead = min(ndead_term, settings['max_ndead'])
    if 'nlives' not in settings or not settings['nlives']:
        assert ndead % nthread == 0, (
            'ndead={0}, nthread={1}'.format(ndead, nthread))
    nsample = ndead // nthread
    nsample += 1  # mimic PolyChord, which includes live point at termination
    # make dead points array
    run = nestcheck.dummy_data.get_dummy_run(
        nthread, nsample, seed=seed, ndim=ndim, logl_range=logl_range)
    run['output'] = {'base_dir': settings['base_dir'],
                     'file_root': settings['file_root']}
    if write_stats:
        nestcheck.write_polychord_output.write_run_output(run)
    if settings['write_resume']:
        # if required, save a dummy resume file
        root = os.path.join(settings['base_dir'], settings['file_root'])
        np.savetxt(root + '.resume', np.zeros(10))


class DummyMPIComm(object):

    """A dummy mpi4py MPI.COMM object for testing."""

    def __init__(self, rank):
        self.rank = rank

    def Get_rank(self):
        """Dummy version of mpi4py MPI.COMM's Get_rank()."""
        return self.rank

    @staticmethod
    def Get_size():  # pylint: disable=invalid-name
        """Dummy version of mpi4py MPI.COMM's Get_size()."""
        return 2

    @staticmethod
    def bcast(_, root=0):
        """Dummy version of mpi4py MPI.COMM's bcast(data, root=0)
        method.
        AssertionError raising is used to allow behavior testing without
        running the whole of the run_dypolychord function in which the call is
        embedded."""
        if root == 0:
            raise AssertionError

if __name__ == '__main__':
    unittest.main()
