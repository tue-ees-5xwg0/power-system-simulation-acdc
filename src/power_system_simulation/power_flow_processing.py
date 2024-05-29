# power_flow_processing.py
"""
In this file the processing of the power system should be done. Power system can be given in a different test file. 
"""

import json
import pprint
import warnings

import pandas as pd

# import power_grid_model as pgm
import pyarrow as pa
import pyarrow.parquet as pq

with warnings.catch_warnings(action="ignore", category=DeprecationWarning):
    # suppress warning about pyarrow as future required dependency
    from pandas import DataFrame

from power_grid_model import CalculationMethod, CalculationType, PowerGridModel, initialize_array
from power_grid_model.utils import json_deserialize, json_serialize
from power_grid_model.validation import assert_valid_batch_data, assert_valid_input_data
from pyarrow import table


class PowerProfileNotFound(Exception):
    pass


class TimestampMismatch(Exception):
    pass


class LoadIDMismatch(Exception):
    pass


class PowerFlow:

    def __init__(self, grid_data: dict) -> None:
        """Load grid_data in class 'PowerFlow' upon instantiation

        Args:
            grid_data: Power grid input data. Class dict.
            active_power_profile: Active power profile time data. Class pyarrow.table.
            reactive_power_profile: Reactive power profile time data. Class pyarrow.table.
        """

        assert_valid_input_data(input_data=grid_data, symmetric=True, calculation_type=CalculationType.power_flow)

        self.grid_data = grid_data

        # do not delete the next two lines!!!!
        # self.active_power_profile = active_power_profile
        # self.reactive_power_profile = reactive_power_profile

        self.model = PowerGridModel(self.grid_data)

    def batch_powerflow(self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame) -> dict:
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
        update_data = {"sym_load": load_profile}

        # Validate batch data
        assert_valid_batch_data(
            input_data=self.grid_data, update_data=update_data, calculation_type=CalculationType.power_flow
        )

        # Run Newton-Raphson power flow
        output_data = self.model.calculate_power_flow(
            update_data=update_data, calculation_method=CalculationMethod.newton_raphson
        )

        return output_data

    def aggregate_voltage_table(
        self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate power flow results into a table with voltage information.

        Args:
            output_data (pd.DataFrame): Output data from power flow calculation.

        Returns:
            pd.DataFrame: Table with voltage information.
        """

        output_data = self.batch_powerflow(
            active_power_profile=active_power_profile, reactive_power_profile=reactive_power_profile
        )

        voltage_table = pd.DataFrame()

        voltage_table["Timestamp"] = active_power_profile.index.tolist()
        voltage_table["max_id"] = output_data["node"][
            :, pd.DataFrame(output_data["node"]["u_pu"][:, :]).idxmax(axis=1).tolist()
        ]["id"][0, :]
        voltage_table["u_pu_max"] = pd.DataFrame(output_data["node"]["u_pu"][:, :]).max(axis=1).tolist()
        voltage_table["min_id"] = output_data["node"][
            :, pd.DataFrame(output_data["node"]["u_pu"][:, :]).idxmin(axis=1).tolist()
        ]["id"][0, :]
        voltage_table["u_pu_min"] = pd.DataFrame(output_data["node"]["u_pu"][:, :]).min(axis=1).tolist()

        return voltage_table

    def aggregate_loading_table(self, output_data: pd.DataFrame) -> pd.DataFrame:

        pass

    # def process_data(self):
    #     """
    #     Do the processing of the grid_data here.
    #     """
    #     pprint.pprint(json.loads(self.grid_data))
    #     dataset = json_deserialize(self.grid_data)
    #     print("components:", dataset.keys())
    #     print(DataFrame(dataset["node"]))

    #     model = PowerGridModel(dataset)
    #     output = model.calculate_power_flow()
    #     print(DataFrame(output["node"]))

    #     # serialized_output = json_serialize(output)
    #     print(serialized_output)

    #     if self.active_power_profile is not None:
    #         print("Active Power Profile Data:")
    #         print(self.active_power_profile)
    #     else:
    #         print("No active power profile data provided.")

    #     if self.reactive_power_profile is not None:
    #         print("Reactive Power Profile Data:")
    #         print(self.reactive_power_profile)
    #     else:
    #         print("No Reactive power profile data provided.")
