import unittest
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
import scipy as sp
from power_grid_model import LoadGenType, PowerGridModel, initialize_array
from power_grid_model.utils import json_deserialize_from_file

import power_system_simulation.graph_processing as gp
import power_system_simulation.power_flow_processing as pfp
import power_system_simulation.power_system_simulation as pss
from power_system_simulation.graph_processing import GraphCycleError, GraphNotFullyConnectedError

# from power_system_simulation.input_data_validity_check import InvalidLVFeederIDError, validity_check, NotExactlyOneSourceError, NotExactlyOneTransformerError, WrongFromNodeLVFeederError  # Import power_system_simpulation.graphy_processing
from power_system_simulation.power_flow_processing import PowerFlow
from power_system_simulation.power_system_simulation import (
    InvalidLVFeederIDError,
    NotExactlyOneSourceError,
    NotExactlyOneTransformerError,
    PowerSim,
    TotalEnergyLoss,
    VoltageDeviation,
    WrongFromNodeLVFeederError,
)


class TestPowerSim(unittest.TestCase):
    def setUp(self):
        # Load data from input_network_data.json
        self.grid_data = json_deserialize_from_file("src/power_system_simulation/input_network_data_2.json")

        # Load the Active Power Profile file
        try:
            self.active_power_profile = pd.read_parquet("src/power_system_simulation/active_power_profile_2.parquet")
        except FileNotFoundError:
            self.fail(
                "Active Power Profile file not found. Please ensure 'active_power_profile.parquet' is in the correct location."
            )

        # Load the EV active power profile file
        try:
            self.ev_active_power_profile = pd.read_parquet(
                "src/power_system_simulation/ev_active_power_profile_2.parquet"
            )
        except FileNotFoundError:
            self.fail(
                "EV Active Power Profile file not found. Please ensure 'active_power_profile.parquet' is in the correct location."
            )

        # Load the Reactive Power Profile file
        try:
            self.reactive_power_profile = pd.read_parquet(
                "src/power_system_simulation/reactive_power_profile_2.parquet"
            )
        except FileNotFoundError:
            self.fail(
                "Reactive Power Profile file not found. Please ensure 'reactive_power_profile.parquet' is in the correct location."
            )

        # declare new PowerSimModel object
        self.psm = pss.PowerSim(grid_data=self.grid_data)

    def test_network_plotter(self):
        void_test = self.psm.network_plotter(plot_criteria=gp.AllEdges)  # Testcase 1 of find network_plotter
        assert void_test == None

        void_test = self.psm.network_plotter(plot_criteria=gp.EnabledEdges)  # Testcase 2 of find network_plotter
        assert void_test == None

    def test_N1(self):
        disabled_edge_id = 16
        table = self.psm.n1_calculations(
            self.grid_data, self.active_power_profile, self.reactive_power_profile, disabled_edge_id
        )

        self.assertIsInstance(table, pd.DataFrame)
        self.assertListEqual(
            list(table.columns),
            ["Alternative_Line_ID", "Max_Loading", "Max_Loading_ID", "Max_Loading_Timestamp"],
        )

        expected_output = pd.DataFrame(
            {
                "Alternative_Line_ID": [24],
                "Max_Loading": [0.0016589657345386518],
                "Max_Loading_ID": [21],
                "Max_Loading_Timestamp": [pd.Timestamp("2025-01-07 10:30:00")],
            }
        )

        expected_output["Alternative_Line_ID"] = expected_output["Alternative_Line_ID"].astype(np.int32)
        expected_output["Max_Loading_ID"] = expected_output["Max_Loading_ID"].astype(np.int32)

        # Compare with expected output
        pd.testing.assert_frame_equal(table, expected_output)

    def test_EV_penetration(self):
        num_houses = 150
        penetration_level = 20
        num_feeders = 7

        voltage_table, loading_table = self.psm.ev_penetration(
            num_houses=num_houses,
            num_feeders=num_feeders,
            penetration_level=penetration_level,
            active_power_profile=self.active_power_profile,
            reactive_power_profile=self.reactive_power_profile,
            ev_active_power_profile=self.ev_active_power_profile,
        )

        # Assertions to verify correct functionality
        # Ensure voltage_table and loading_table are DataFrames
        self.assertIsInstance(voltage_table, pd.DataFrame)
        self.assertIsInstance(loading_table, pd.DataFrame)

        # Check if voltage_table and loading_table have the expected structure
        self.assertFalse(voltage_table.empty, "Voltage table should not be empty")
        self.assertFalse(loading_table.empty, "Loading table should not be empty")

        expected_volt = pd.DataFrame(
            {
                "Timestamp": [
                    pd.Timestamp("2025-01-01 00:00:00"),
                    pd.Timestamp("2025-01-01 00:15:00"),
                    pd.Timestamp("2025-01-01 00:30:00"),
                    pd.Timestamp("2025-01-01 00:45:00"),
                    pd.Timestamp("2025-01-01 01:00:00"),
                ],
                "Max_Voltage": [1.072931, 1.075911, 1.069725, 1.073244, 1.072924],
                "Max_Voltage_Node": [1, 1, 1, 1, 1],
                "Min_Voltage": [1.049819, 1.050022, 1.049603, 1.049842, 1.049819],
                "Min_Voltage_Node": [0, 0, 0, 0, 0],
            }
        )
        expected_volt.set_index("Timestamp", inplace=True)
        expected_volt["Max_Voltage_Node"] = expected_volt["Max_Voltage_Node"].astype(np.int32)
        expected_volt["Min_Voltage_Node"] = expected_volt["Min_Voltage_Node"].astype(np.int32)

        pd.testing.assert_frame_equal(voltage_table.head(), expected_volt)

        expected_load = pd.DataFrame(
            {
                "Line_ID": [16, 17, 18, 19, 20],
                "Total_Loss": [26.709511, 1.128073, 9.100636, 1.220324, 27.361620],
                "Max_Loading": [6.869324e-05, 1.653650e-03, 3.414478e-05, 1.543576e-03, 7.086133e-05],
                "Max_Loading_Timestamp": [
                    pd.Timestamp("2025-01-04 06:30:00"),
                    pd.Timestamp("2025-01-04 09:45:00"),
                    pd.Timestamp("2025-01-07 10:45:00"),
                    pd.Timestamp("2025-01-07 10:45:00"),
                    pd.Timestamp("2025-01-07 10:45:00"),
                ],
                "Min_Loading": [1.253601e-05, 2.697708e-04, 5.617314e-06, 2.496785e-04, 1.172002e-05],
                "Min_Loading_Timestamp": [
                    pd.Timestamp("2025-01-08 12:30:00"),
                    pd.Timestamp("2025-01-08 11:30:00"),
                    pd.Timestamp("2025-01-05 17:45:00"),
                    pd.Timestamp("2025-01-05 17:45:00"),
                    pd.Timestamp("2025-01-02 14:30:00"),
                ],
            }
        )
        expected_load["Line_ID"] = expected_load["Line_ID"].astype(np.int32)
        expected_load.set_index("Line_ID", inplace=True)

        pd.testing.assert_frame_equal(loading_table.head(), expected_load)

    def test_optimal_tap_position_energy_loss(self):
        optimal_tap = self.psm.optimal_tap_position(
            active_power_profile=self.active_power_profile,
            reactive_power_profile=self.reactive_power_profile,
            opt_criteria=TotalEnergyLoss,
        )

        # Assertions to verify correct functionality for energy loss criteria
        self.assertIsInstance(optimal_tap, int, "Optimal tap position should be an integer")

        expected = 5

        self.assertEqual(optimal_tap, expected)

    def test_optimal_tap_position_voltage_deviation(self):
        optimal_tap = self.psm.optimal_tap_position(
            active_power_profile=self.active_power_profile,
            reactive_power_profile=self.reactive_power_profile,
            opt_criteria=VoltageDeviation,
        )

        # Assertions to verify correct functionality for voltage deviation criteria
        self.assertIsInstance(optimal_tap, int, "Optimal tap position should be an integer")

        expected = 1

        self.assertEqual(optimal_tap, expected)

    def test_InvalidLVFeederIDError(self):

        # node
        node = initialize_array("input", "node", 3)
        node["id"] = [2, 4, 6]
        node["u_rated"] = [1e4, 4e2, 4e2]

        # load
        sym_load = initialize_array("input", "sym_load", 1)
        sym_load["id"] = [7]
        sym_load["node"] = [6]
        sym_load["status"] = [1]
        sym_load["type"] = [LoadGenType.const_power]
        sym_load["p_specified"] = [1e3]
        sym_load["q_specified"] = [5e3]

        # source
        source = initialize_array("input", "source", 1)
        source["id"] = [1]
        source["node"] = [2]
        source["status"] = [1]
        source["u_ref"] = [1.0]

        # line
        line = initialize_array("input", "line", 1)
        line["id"] = [5]
        line["from_node"] = [4]
        line["to_node"] = [6]
        line["from_status"] = [1]
        line["to_status"] = [1]
        line["r1"] = [10.0]
        line["x1"] = [0.0]
        line["c1"] = [0.0]
        line["tan1"] = [0.0]

        # transformer
        transformer = initialize_array("input", "transformer", 1)
        transformer["id"] = [3]
        transformer["from_node"] = [2]
        transformer["to_node"] = [4]
        transformer["from_status"] = [1]
        transformer["to_status"] = [1]
        transformer["u1"] = [1e4]
        transformer["u2"] = [4e2]
        transformer["sn"] = [1e5]
        transformer["uk"] = [0.1]
        transformer["pk"] = [1e3]
        transformer["i0"] = [1.0e-6]
        transformer["p0"] = [0.1]
        transformer["winding_from"] = [2]
        transformer["winding_to"] = [1]
        transformer["clock"] = [5]
        transformer["tap_side"] = [0]
        transformer["tap_pos"] = [3]
        transformer["tap_min"] = [-11]
        transformer["tap_max"] = [9]
        transformer["tap_size"] = [100]

        # all
        input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}

        with pytest.raises(InvalidLVFeederIDError) as excinfo:
            lv_feeders = [2]
            PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
        assert str(excinfo.value) == "LV feeder IDs are not valid line IDs"

        with pytest.raises(InvalidLVFeederIDError) as excinfo:
            lv_feeders = [20]
            PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
        assert str(excinfo.value) == "LV feeder IDs are not valid line IDs"


def test_NotExactlyOneSourceError():

    # node
    node = initialize_array("input", "node", 3)
    node["id"] = [2, 4, 6]
    node["u_rated"] = [1e4, 4e2, 4e2]

    # load
    sym_load = initialize_array("input", "sym_load", 1)
    sym_load["id"] = [7]
    sym_load["node"] = [6]
    sym_load["status"] = [1]
    sym_load["type"] = [LoadGenType.const_power]
    sym_load["p_specified"] = [1e3]
    sym_load["q_specified"] = [5e3]

    # line
    line = initialize_array("input", "line", 1)
    line["id"] = [5]
    line["from_node"] = [4]
    line["to_node"] = [6]
    line["from_status"] = [1]
    line["to_status"] = [1]
    line["r1"] = [10.0]
    line["x1"] = [0.0]
    line["c1"] = [0.0]
    line["tan1"] = [0.0]

    # transformer
    transformer = initialize_array("input", "transformer", 1)
    transformer["id"] = [3]
    transformer["from_node"] = [2]
    transformer["to_node"] = [4]
    transformer["from_status"] = [1]
    transformer["to_status"] = [1]
    transformer["u1"] = [1e4]
    transformer["u2"] = [4e2]
    transformer["sn"] = [1e5]
    transformer["uk"] = [0.1]
    transformer["pk"] = [1e3]
    transformer["i0"] = [1.0e-6]
    transformer["p0"] = [0.1]
    transformer["winding_from"] = [2]
    transformer["winding_to"] = [1]
    transformer["clock"] = [5]
    transformer["tap_side"] = [0]
    transformer["tap_pos"] = [3]
    transformer["tap_min"] = [-11]
    transformer["tap_max"] = [9]
    transformer["tap_size"] = [100]

    lv_feeders = []

    with pytest.raises(NotExactlyOneSourceError) as excinfo:
        # source
        source = initialize_array("input", "source", 2)
        source["id"] = [1, 10]
        source["node"] = [2, 4]
        source["status"] = [1, 1]
        source["u_ref"] = [1.0, 1.0]
        # all
        input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "There is not exactly one source"

    with pytest.raises(NotExactlyOneSourceError) as excinfo:
        # source
        source = initialize_array("input", "source", 0)
        source["id"] = []
        source["node"] = []
        source["status"] = []
        source["u_ref"] = []
        # all
        input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "There is not exactly one source"


def test_NotExactlyOneTransformerError():

    # node
    node = initialize_array("input", "node", 3)
    node["id"] = [2, 4, 6]
    node["u_rated"] = [1e4, 4e2, 4e2]

    # load
    sym_load = initialize_array("input", "sym_load", 1)
    sym_load["id"] = [7]
    sym_load["node"] = [6]
    sym_load["status"] = [1]
    sym_load["type"] = [LoadGenType.const_power]
    sym_load["p_specified"] = [1e3]
    sym_load["q_specified"] = [5e3]

    # line
    line = initialize_array("input", "line", 1)
    line["id"] = [5]
    line["from_node"] = [4]
    line["to_node"] = [6]
    line["from_status"] = [1]
    line["to_status"] = [1]
    line["r1"] = [10.0]
    line["x1"] = [0.0]
    line["c1"] = [0.0]
    line["tan1"] = [0.0]

    # source
    source = initialize_array("input", "source", 1)
    source["id"] = [1]
    source["node"] = [2]
    source["status"] = [1]
    source["u_ref"] = [1.0]

    lv_feeders = [5]

    with pytest.raises(NotExactlyOneTransformerError) as excinfo:
        # node
        node = initialize_array("input", "node", 4)
        node["id"] = [2, 4, 6, 8]
        node["u_rated"] = [1e4, 4e2, 4e2, 4e2]
        # transformer
        transformer = initialize_array("input", "transformer", 2)
        transformer["id"] = [3, 10]
        transformer["from_node"] = [2, 6]
        transformer["to_node"] = [4, 8]
        transformer["from_status"] = [1, 1]
        transformer["to_status"] = [1, 1]
        transformer["u1"] = [1e4, 4e2]
        transformer["u2"] = [4e2, 4e2]
        transformer["sn"] = [1e5, 1e5]
        transformer["uk"] = [0.1, 0.1]
        transformer["pk"] = [1e3, 1e3]
        transformer["i0"] = [1.0e-6, 1.0e-6]
        transformer["p0"] = [0.1, 0.1]
        transformer["winding_from"] = [2, 2]
        transformer["winding_to"] = [1, 2]
        transformer["clock"] = [5, 6]
        transformer["tap_side"] = [0, 0]
        transformer["tap_pos"] = [3, 3]
        transformer["tap_min"] = [-11, -11]
        transformer["tap_max"] = [9, 9]
        transformer["tap_size"] = [100, 100]
        # all
        input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "There is not exactly one transformer"

    with pytest.raises(NotExactlyOneTransformerError) as excinfo:
        # transformer
        transformer = initialize_array("input", "transformer", 0)
        transformer["id"] = []
        transformer["from_node"] = []
        transformer["to_node"] = []
        transformer["from_status"] = []
        transformer["to_status"] = []
        transformer["u1"] = []
        transformer["u2"] = []
        transformer["sn"] = []
        transformer["uk"] = []
        transformer["pk"] = []
        transformer["i0"] = []
        transformer["p0"] = []
        transformer["winding_from"] = []
        transformer["winding_to"] = []
        transformer["clock"] = []
        transformer["tap_side"] = []
        transformer["tap_pos"] = []
        transformer["tap_min"] = []
        transformer["tap_max"] = []
        transformer["tap_size"] = []
        # all
        input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "There is not exactly one transformer"


def test_WrongFromNodeLVFeederError():

    # node
    node = initialize_array("input", "node", 4)
    node["id"] = [2, 4, 6, 8]
    node["u_rated"] = [1e4, 4e2, 4e2, 4e2]

    # source
    source = initialize_array("input", "source", 1)
    source["id"] = [1]
    source["node"] = [2]
    source["status"] = [1]
    source["u_ref"] = [1.0]

    # load
    sym_load = initialize_array("input", "sym_load", 1)
    sym_load["id"] = [7]
    sym_load["node"] = [6]
    sym_load["status"] = [1]
    sym_load["type"] = [LoadGenType.const_power]
    sym_load["p_specified"] = [1e3]
    sym_load["q_specified"] = [5e3]

    # line
    line = initialize_array("input", "line", 2)
    line["id"] = [5, 10]
    line["from_status"] = [1, 1]
    line["to_status"] = [1, 1]
    line["r1"] = [10.0, 10.00]
    line["x1"] = [0.0, 0.0]
    line["c1"] = [0.0, 0.0]
    line["tan1"] = [0.0, 0.0]

    # transformer
    transformer = initialize_array("input", "transformer", 1)
    transformer["id"] = [3]
    transformer["from_node"] = [2]
    transformer["to_node"] = [4]
    transformer["from_status"] = [1]
    transformer["to_status"] = [1]
    transformer["u1"] = [1e4]
    transformer["u2"] = [4e2]
    transformer["sn"] = [1e5]
    transformer["uk"] = [0.1]
    transformer["pk"] = [1e3]
    transformer["i0"] = [1.0e-6]
    transformer["p0"] = [0.1]
    transformer["winding_from"] = [2]
    transformer["winding_to"] = [1]
    transformer["clock"] = [5]
    transformer["tap_side"] = [0]
    transformer["tap_pos"] = [3]
    transformer["tap_min"] = [-11]
    transformer["tap_max"] = [9]
    transformer["tap_size"] = [100]

    lv_feeders = [5]

    with pytest.raises(WrongFromNodeLVFeederError) as excinfo:
        # line
        line["from_node"] = [6, 4]
        line["to_node"] = [8, 6]
        # transformer
        transformer["from_node"] = [2]
        transformer["to_node"] = [4]
        # all
        input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "The LV Feeder from_node does not correspond with the transformer to_node"

    with pytest.raises(WrongFromNodeLVFeederError) as excinfo:
        # line
        line["from_node"] = [4, 4]
        line["to_node"] = [6, 8]
        # transformer
        transformer["from_node"] = [2]
        transformer["to_node"] = [8]
        # all
        input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "The LV Feeder from_node does not correspond with the transformer to_node"


def test_CycleError():

    # node
    node = initialize_array("input", "node", 3)
    node["id"] = [2, 4, 6]
    node["u_rated"] = [4e2, 4e2, 4e2]

    # load
    sym_load = initialize_array("input", "sym_load", 1)
    sym_load["id"] = [7]
    sym_load["node"] = [6]
    sym_load["status"] = [1]
    sym_load["type"] = [LoadGenType.const_power]
    sym_load["p_specified"] = [1e3]
    sym_load["q_specified"] = [5e3]

    # line
    line = initialize_array("input", "line", 2)
    line["id"] = [5, 20]
    line["from_node"] = [4, 2]
    line["to_node"] = [6, 6]
    line["from_status"] = [1, 1]
    line["to_status"] = [1, 1]
    line["r1"] = [10.0, 10.0]
    line["x1"] = [0.0, 0.0]
    line["c1"] = [0.0, 0.0]
    line["tan1"] = [0.0, 0.0]

    # source
    source = initialize_array("input", "source", 1)
    source["id"] = [1]
    source["node"] = [2]
    source["status"] = [1]
    source["u_ref"] = [1.0]

    # transformer
    transformer = initialize_array("input", "transformer", 1)
    transformer["id"] = [3]
    transformer["from_node"] = [2]
    transformer["to_node"] = [4]
    transformer["from_status"] = [1]
    transformer["to_status"] = [1]
    transformer["u1"] = [1e4]
    transformer["u2"] = [4e2]
    transformer["sn"] = [1e5]
    transformer["uk"] = [0.1]
    transformer["pk"] = [1e3]
    transformer["i0"] = [1.0e-6]
    transformer["p0"] = [0.1]
    transformer["winding_from"] = [2]
    transformer["winding_to"] = [1]
    transformer["clock"] = [5]
    transformer["tap_side"] = [0]
    transformer["tap_pos"] = [3]
    transformer["tap_min"] = [-11]
    transformer["tap_max"] = [9]
    transformer["tap_size"] = [100]
    # all
    input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}

    lv_feeders = [5]

    with pytest.raises(GraphCycleError) as excinfo:
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "Cycle found"


def test_GraphNotFullyConnectedError():

    # node
    node = initialize_array("input", "node", 4)
    node["id"] = [2, 4, 6, 45]
    node["u_rated"] = [1e4, 4e2, 4e2, 6e2]

    # load
    sym_load = initialize_array("input", "sym_load", 1)
    sym_load["id"] = [7]
    sym_load["node"] = [6]
    sym_load["status"] = [1]
    sym_load["type"] = [LoadGenType.const_power]
    sym_load["p_specified"] = [1e3]
    sym_load["q_specified"] = [5e3]

    # line
    line = initialize_array("input", "line", 1)
    line["id"] = [5]
    line["from_node"] = [4]
    line["to_node"] = [6]
    line["from_status"] = [1]
    line["to_status"] = [1]
    line["r1"] = [10.0]
    line["x1"] = [0.0]
    line["c1"] = [0.0]
    line["tan1"] = [0.0]

    # source
    source = initialize_array("input", "source", 1)
    source["id"] = [1]
    source["node"] = [2]
    source["status"] = [1]
    source["u_ref"] = [1.0]

    # transformer
    transformer = initialize_array("input", "transformer", 1)
    transformer["id"] = [3]
    transformer["from_node"] = [2]
    transformer["to_node"] = [4]
    transformer["from_status"] = [1]
    transformer["to_status"] = [1]
    transformer["u1"] = [1e4]
    transformer["u2"] = [4e2]
    transformer["sn"] = [1e5]
    transformer["uk"] = [0.1]
    transformer["pk"] = [1e3]
    transformer["i0"] = [1.0e-6]
    transformer["p0"] = [0.1]
    transformer["winding_from"] = [2]
    transformer["winding_to"] = [1]
    transformer["clock"] = [5]
    transformer["tap_side"] = [0]
    transformer["tap_pos"] = [3]
    transformer["tap_min"] = [-11]
    transformer["tap_max"] = [9]
    transformer["tap_size"] = [100]
    # all
    input_data = {"node": node, "line": line, "sym_load": sym_load, "source": source, "transformer": transformer}

    lv_feeders = [5]

    with pytest.raises(GraphNotFullyConnectedError) as excinfo:
        PowerSim(grid_data=input_data, lv_feeders=lv_feeders)
    assert str(excinfo.value) == "Graph not fully connected. Cannot reach all vertices."


if __name__ == "__main__":
    unittest.main()
