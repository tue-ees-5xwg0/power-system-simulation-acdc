"""
`power_flow_processing.py` contains the class `PowerFlow`. 
This class defines and validates a grid based on `power_grid_model.PowerGridModel`

It is initialized with parameters:
`def __init__(self, grid_data: dict) -> None`

`grid_data` must be provided in `power_grid_model` format. Refer to: 
https://power-grid-model.readthedocs.io/en/stable/quickstart.html#input-data

The object saves:
1. `self.model`
2. `self.grid_data`

The class contains the functions: 
1. `batch_powerflow(`
   `     self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame, tap_value=0`
   ` ) -> dict`
2. `aggregate_voltage_table(`
   `     self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame`
   ` ) -> pd.DataFrame`
3. `aggregate_loading_table(`
   `     self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame, tap_value=0`
   ` ) -> pd.DataFrame`
"""

import numpy as np
import pandas as pd
import scipy as sp
from power_grid_model import CalculationMethod, CalculationType, PowerGridModel, initialize_array
from power_grid_model.validation import assert_valid_batch_data, assert_valid_input_data


class PowerProfileNotFound(Exception):
    """Raises error if power profile is not found"""


class TimestampMismatch(Exception):
    """Raises error if timestamps of power profiles do no not match"""


class LoadIDMismatch(Exception):
    """Raises error if load IDs of power profiles do no not match"""


class PowerFlow:
    """
    In this class are the functionalities of assignment 2,
    including the initialization of the PGM grid and the aggregation functions for
    the voltage table and loading table
    """

    def __init__(self, grid_data: dict) -> None:
        """Load and validate grid_data in class 'PowerFlow' upon instantiation

        Args:
            grid_data: Power grid input data. Class dict.
        """

        assert_valid_input_data(input_data=grid_data, symmetric=True, calculation_type=CalculationType.power_flow)

        self.grid_data = grid_data

        self.model = PowerGridModel(self.grid_data)

    def batch_powerflow(
        self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame, tap_value=0
    ) -> dict:
        """
        Create a batch update dataset and calculate power flow.

        Args:
            active_power_profile: DataFrame with columns ['Timestamp', '8', '9', '10', ...]
            reactive_power_profile: DataFrame with columns ['Timestamp', '8', '9', '10', ...]

        Returns:
            pd.DataFrame: Power flow solution data.
        """
        # check if any power profile is provided
        if active_power_profile is None:
            raise PowerProfileNotFound("No active power profile provided.")

        if reactive_power_profile is None:
            raise PowerProfileNotFound("No reactive power profile provided.")

        # check if timestamps are equal in value and lengths
        if active_power_profile.index.to_list() != reactive_power_profile.index.to_list():
            raise TimestampMismatch("Timestamps of active and reactive power profiles do not match.")

        if active_power_profile.columns.to_list() != reactive_power_profile.columns.to_list():
            raise LoadIDMismatch("Load IDs in given power profiles do not match")

        load_profile = initialize_array(
            "update",
            "sym_load",
            (len(active_power_profile.index.to_list()), len(active_power_profile.columns.to_list())),
        )

        load_profile["id"] = active_power_profile.columns.tolist()
        load_profile["p_specified"] = active_power_profile.values.tolist()
        load_profile["q_specified"] = reactive_power_profile.values.tolist()

        # Construct the update data
        if tap_value != 0:
            tap_profile = initialize_array("update", "transformer", (len(active_power_profile.values.tolist()), 1))
            tap_profile["id"] = self.grid_data["transformer"]["id"]
            tap_profile["tap_pos"] = tap_value

            update_data = {"sym_load": load_profile, "transformer": tap_profile}

        else:
            update_data = {"sym_load": load_profile}

        # Validate batch data
        assert_valid_batch_data(
            input_data=self.grid_data, update_data=update_data, calculation_type=CalculationType.power_flow
        )

        # Run Newton-Raphson power flow
        output_data = self.model.calculate_power_flow(
            update_data=update_data, calculation_method=CalculationMethod.newton_raphson, threading=0
        )

        return output_data

    def aggregate_voltage_table(
        self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregates power flow results into a table with voltage information.
        The table contains the timestamp as index and displays the following information per timestamp:
        - Maximum p.u. voltage of all the nodes for this timestamp
        - The node ID with the maximum p.u. voltage
        - Minimum p.u. voltage of all the nodes for this timestamp
        - The node ID with the minimum p.u. voltage

        Args:
            active_power_profile: DataFrame with columns ['Timestamp', '8', '9', '10', ...]
            reactive_power_profile: DataFrame with columns ['Timestamp', '8', '9', '10', ...]

        Returns:
            voltage_table: DataFrame with voltage information.
        """

        output_data = self.batch_powerflow(
            active_power_profile=active_power_profile, reactive_power_profile=reactive_power_profile
        )

        node_data = output_data["node"]
        voltage_data = node_data["u_pu"]

        max_voltage = voltage_data.max(axis=1)
        max_voltage_node = node_data["id"][np.arange(voltage_data.shape[0]), voltage_data.argmax(axis=1)]
        min_voltage = voltage_data.min(axis=1)
        min_voltage_node = node_data["id"][np.arange(voltage_data.shape[0]), voltage_data.argmin(axis=1)]

        voltage_table = pd.DataFrame(
            {
                "Timestamp": active_power_profile.index,
                "Max_Voltage": max_voltage,
                "Max_Voltage_Node": max_voltage_node,
                "Min_Voltage": min_voltage,
                "Min_Voltage_Node": min_voltage_node,
            }
        )

        voltage_table.set_index("Timestamp", inplace=True)

        return voltage_table

    def aggregate_loading_table(
        self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame, tap_value=0
    ) -> pd.DataFrame:
        """
        Aggregates power flow results into a table with line loading information.
        The table contains the line ID as index and displays the following information per line:
        - Energy loss of the line across the timeline in kWh
        - Maximum loading in p.u. of the line across the whole timeline
        - Timestamp of this maximum loading moment
        - Minimum loading in p.u. of the line across the whole timeline
        - Timestamp of this minimum loading moment

        Args:
            active_power_profile: DataFrame with columns ['Timestamp', '8', '9', '10', ...]
            reactive_power_profile: DataFrame with columns ['Timestamp', '8', '9', '10', ...]

        Returns:
            loading_table: DataFrame with loading information.
        """

        output_data = self.batch_powerflow(
            active_power_profile=active_power_profile,
            reactive_power_profile=reactive_power_profile,
            tap_value=tap_value,
        )

        line_data = output_data["line"]
        line_ids = line_data["id"][0, :]

        # Extract power data
        p_from = pd.DataFrame(line_data["p_from"][:, :], columns=line_ids)
        p_to = pd.DataFrame(line_data["p_to"][:, :], columns=line_ids)

        # Calculate power loss and energy loss
        p_loss = (p_from + p_to) * 1e-3
        e_loss = sp.integrate.trapezoid(p_loss, dx=1.0, axis=0)

        # Compute maximum and minimum loading
        loading = pd.DataFrame(line_data["loading"][:, :], columns=line_ids)
        max_loading = loading.max()
        min_loading = loading.min()

        max_loading_id = loading.idxmax()
        min_loading_id = loading.idxmin()

        max_loading_time = active_power_profile.index[max_loading_id]
        min_loading_time = active_power_profile.index[min_loading_id]

        # Construct loading table
        loading_table = pd.DataFrame(
            {
                "Line_ID": line_ids,
                "Total_Loss": e_loss,
                "Max_Loading": max_loading.values,
                "Max_Loading_Timestamp": max_loading_time.values,
                "Min_Loading": min_loading.values,
                "Min_Loading_Timestamp": min_loading_time.values,
            }
        )

        loading_table.set_index("Line_ID", inplace=True)

        return loading_table
