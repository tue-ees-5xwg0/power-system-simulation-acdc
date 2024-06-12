import graph_processing as gp
import pandas as pd
import power_flow_processing as pfp

# write exceptions here


class TotalEnergyLoss:
    pass


class VoltageDeviation:
    pass


class PowerSim:
    def __init__(self, grid_data: dict) -> None:
        self.PowerSimModel = pfp.PowerFlow(grid_data=grid_data)

    def example_code(self):
        print("Who reads trek een bak")

    def n1_calculations():

        pass

    def ev_penetration():
        pass

    def optimal_tap_position(
        self, active_power_profile: pd.DataFrame, reactive_power_profile: pd.DataFrame, opt_criteria=TotalEnergyLoss
    ) -> int:
        grid_data = self.PowerSimModel.grid_data

        update_tap = range(grid_data["transformer"]["tap_max"][0], grid_data["transformer"]["tap_min"][0] + 1)

        energy_loss_aggregate = {}
        voltage_deviation = {}
        voltage_table = {}

        # may god help us with this function
        # output_data = {}

        for i in update_tap:
            # output_data[f"tap{i}"] = self.PowerSimModel.batch_powerflow(
            #     active_power_profile=active_power_profile, reactive_power_profile=reactive_power_profile, tap_value=i
            # )

            if opt_criteria == TotalEnergyLoss:
                energy_loss_aggregate[f"{i}"] = sum(
                    (
                        self.PowerSimModel.aggregate_loading_table(
                            active_power_profile=active_power_profile,
                            reactive_power_profile=reactive_power_profile,
                            tap_value=i,
                        )
                    )["Total_Loss"]
                )

            elif opt_criteria == VoltageDeviation:
                voltage_table[f"{i}"] = self.PowerSimModel.aggregate_voltage_table(
                    active_power_profile=active_power_profile, reactive_power_profile=reactive_power_profile
                )
                voltage_deviation[f"{i}"] = sum(
                    (pd.DataFrame(voltage_table[f"{i}"][["Max_Voltage", "Min_Voltage"]] - 1).max(axis=1)).tolist()
                ) / len((pd.DataFrame(voltage_table[f"{i}"][["Max_Voltage", "Min_Voltage"]] - 1).max(axis=1)).tolist())

        if opt_criteria == TotalEnergyLoss:
            optimal_tap = int(min(energy_loss_aggregate, key=lambda k: energy_loss_aggregate[k]))

        elif opt_criteria == VoltageDeviation:
            # print(pd.DataFrame(voltage_deviation.keys()))
            optimal_tap = int(min(voltage_deviation, key=lambda k: voltage_deviation[k]))
            # print(optimal_tap)

        return optimal_tap