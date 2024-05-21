# power_flow_processing.py
"""
In this file the processing of the power system should be done. Power system can be given in a different test file. 
"""

import json
import pprint

from pandas import DataFrame
from power_grid_model import PowerGridModel
from power_grid_model.utils import json_deserialize, json_serialize


class PowerFlow:
    """
    General documentation of this class.
    You need to describe the purpose of this class and the functions in it.
    We are initializing the data here.
    """

    def __init__(self, data=None, power_profile=None, reactive_power_profile=None):
        # Load data upon instantiation
        self.data = data
        self.power_profile = power_profile
        self.reactive_power_profile = reactive_power_profile

    def process_data(self):
        """
        Do the processing of the data here.
        """
        pprint.pprint(json.loads(self.data))
        dataset = json_deserialize(self.data)
        print("components:", dataset.keys())
        print(DataFrame(dataset["node"]))

        model = PowerGridModel(dataset)
        output = model.calculate_power_flow()
        print(DataFrame(output["node"]))

        serialized_output = json_serialize(output)
        print(serialized_output)

        if self.power_profile is not None:
            print("Active Power Profile Data:")
            print(self.power_profile)
        else:
            print("No active power profile data provided.")

        if self.reactive_power_profile is not None:
            print("Reactive Power Profile Data:")
            print(self.reactive_power_profile)
        else:
            print("No Reactive power profile data provided.")
