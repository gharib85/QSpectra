import numpy as np
import unittest
from numpy.testing import assert_allclose

from qspectra import hamiltonian, GAUSSIAN_SD_FWHM


class TestElectronicHamiltonian(unittest.TestCase):
    def setUp(self):
        self.M = np.array([[1., 0], [0, 3]])
        self.H_el = hamiltonian.ElectronicHamiltonian(
            self.M, bath=None, dipoles=[[1, 0, 0], [0, 1, 0]], disorder=1,
            energy_spread_extra=1.0)

    def test_properties(self):
        self.assertEqual(self.H_el.energy_spread_extra, 1)
        self.assertEqual(self.H_el.n_sites, 2)
        self.assertEqual(self.H_el.n_states('gef'), 4)
        self.assertEqual(self.H_el.freq_step, 10.0)
        self.assertEqual(self.H_el.time_step, 0.1)
        assert_allclose(self.H_el.H('e'), self.M)
        assert_allclose(self.H_el.E('g'), [0])
        assert_allclose(self.H_el.E('ge'), [0, 1, 3])
        assert_allclose(self.H_el.E('gef'), [0, 1, 3, 4])
        assert_allclose(self.H_el.ground_state('ge'),
                        [[1, 0, 0], [0, 0, 0], [0, 0, 0]])
        self.assertEqual(self.H_el.mean_excitation_freq, 2)
        assert_allclose(self.H_el.number_operator(1, 'gef'),
                        np.diag([0, 0, 1, 1]))
        assert_allclose(self.H_el.number_operator(0, 'ge'),
                        np.diag([0, 1, 0]))
        assert_allclose(self.H_el.dipole_operator('gef', 'x', '-+'),
                        [[0, 1, 0, 0], [1, 0, 0, 0],
                         [0, 0, 0, 1], [0, 0, 1, 0]])
        H_no_dipoles = hamiltonian.ElectronicHamiltonian(self.M)
        with self.assertRaises(hamiltonian.HamiltonianError):
            H_no_dipoles.dipole_operator()
        with self.assertRaises(hamiltonian.HamiltonianError):
            self.H_el.system_bath_couplings()

    def test_rotating_frame(self):
        H_rw = self.H_el.in_rotating_frame(2)
        assert_allclose(H_rw.H('e'), [[-1, 0], [0, 1]])
        self.assertItemsEqual(H_rw.E('gef'), [0, 1, -1, 0])
        self.assertEqual(H_rw.mean_excitation_freq, 2)
        self.assertEqual(H_rw.freq_step, 6.0)

        H_rw2 = H_rw.in_rotating_frame(3)
        self.assertEqual(H_rw2.mean_excitation_freq, 2)
        assert_allclose(H_rw2.H('e'), [[-2, 0], [0, 0]])

    def test_sample_ensemble(self):
        H_sampled = list(self.H_el.sample_ensemble(1))[0]
        self.assertEqual(H_sampled.freq_step, self.H_el.freq_step)
        self.assertEqual(H_sampled.time_step, self.H_el.time_step)
        self.assertEqual(H_sampled.in_rotating_frame().time_step,
                         self.H_el.in_rotating_frame().time_step)
        H_rw_sampled = list(self.H_el.in_rotating_frame().sample_ensemble(1))[0]
        assert_allclose(H_sampled.in_rotating_frame().H('gef'),
                        H_rw_sampled.H('gef'))
        H_sampled_2 = list(self.H_el.sample_ensemble(1,
            random_orientations=True))[0]
        self.assertAlmostEqual(np.dot(*H_sampled_2.dipoles), 0)

        def disorder(random_state):
            return np.diag(GAUSSIAN_SD_FWHM * random_state.randn(2))
        H_matching_seed = hamiltonian.ElectronicHamiltonian(
            self.M, disorder=disorder, random_seed=0)
        H_non_matching_seed = hamiltonian.ElectronicHamiltonian(
            self.M, disorder=disorder, random_seed=1)
        assert_allclose(H_sampled.H('gef'),
                        list(H_matching_seed.sample_ensemble(1))[0].H('gef'))
        self.assertFalse(np.allclose(
            H_sampled.H('gef'),
            list(H_non_matching_seed.sample_ensemble(1))[0].H('gef')))

    def test_thermal_state(self):
        assert_allclose(hamiltonian.thermal_state(self.H_el.H_1exc, 2),
                        1 / (np.exp(0.5) + np.exp(-0.5)) *
                        np.array([[np.exp(0.5), 0], [0, np.exp(-0.5)]]))


class DummyBath(object):
    temperature = 2


class TestVibronicHamiltonian(unittest.TestCase):
    def setUp(self):
        H_E = hamiltonian.ElectronicHamiltonian([[1.0]], bath=DummyBath())
        self.H_EV = hamiltonian.VibronicHamiltonian(H_E, [2], [10], [[5]])

    def test_properties(self):
        self.assertEqual(self.H_EV.n_sites, 1)
        self.assertEqual(self.H_EV.n_vibrational_states, 2)
        self.assertEqual(self.H_EV.n_states('gef'), 4)
        assert_allclose(self.H_EV.H('ge'),
                        [[0, 0, 0, 0],
                         [0, 10, 0, 0],
                         [0, 0, 1, 5],
                         [0, 0, 5, 11]])
        assert_allclose(self.H_EV.ground_state('g'),
                        1 / (1 + np.exp(-5)) * np.diag([1, np.exp(-5)]))

    def test_sample_ensemble(self):
        H_sampled = list(self.H_EV.sample_ensemble(1))[0]
        self.assertEqual(H_sampled.freq_step, self.H_EV.freq_step)
        self.assertEqual(H_sampled.time_step, self.H_EV.time_step)
        self.assertEqual(H_sampled.in_rotating_frame().time_step,
                         self.H_EV.in_rotating_frame().time_step)
        H_rw_sampled = list(self.H_EV.in_rotating_frame().sample_ensemble(1))[0]
        assert_allclose(H_sampled.in_rotating_frame().H('gef'),
                        H_rw_sampled.H('gef'))

    def test_operators(self):
        assert_allclose(self.H_EV.system_bath_couplings('ge'),
                        [[[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]])
