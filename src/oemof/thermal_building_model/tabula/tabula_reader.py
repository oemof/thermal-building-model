"""BuildingConfig Model

SPDX-FileCopyrightText: Maximilian Hillen <maximilian.hillen@dlr.de>

"""
import pandas as pd
from oemof.thermal_building_model.helpers.path_helper import get_project_root
from oemof.thermal_building_model.helpers.calculate_gain_by_sun import Window
import os
import warnings
from dataclasses import dataclass, field, fields


@dataclass
class BuildingConfig5RC:
    r"""
    The BuildingConfig gets generated by the function build_building_config of the building class

    Parameters
    ----------
    h_ve: numeric :
        Value which describes the conductance to ventilation in W/K.
    h_tr_w : numeric
        Value which describes the conductance to exterior through glazed surfaces in W/K.
    h_tr_em : numeric
        Value which describes the conductance of opaque surfaces to exterior in W/K.
    h_tr_is : numeric
        Value which describes the conductance from the conditioned air to interior zone surface in W/K.
    mass_area : list
        Value which describes the effective mass area in m2
    h_tr_ms : numeric
        Value which describes the transmittance from the internal air to the thermal mass in W/K.
    c_m : numeric
        Value of room capacitance in kWh/K
    floor_area : numeric
        Value of the floor area in m2.
    heat_transfer_coefficient_ventilation : numeric
        Value of...
    total_air_change_rate : numeric
        Value of total air changes in m3/s
    Notes
    -----
    Examples
    --------
    """
    total_internal_area: float
    h_ve: float
    h_tr_w: float
    h_tr_em: float
    h_tr_is: float
    mass_area: float
    h_tr_ms: float
    c_m: float
    floor_area: float
    heat_transfer_coefficient_ventilation: float
    total_air_change_rate: float


@dataclass
class BuildingParameters:
    floor_area: float
    heat_transfer_coefficient_ventilation: float
    total_air_change_rate: float
    room_height: float
    a_roof: dict = field(default_factory=dict)
    u_roof: dict = field(default_factory=dict)
    b_roof: dict = field(default_factory=dict)
    a_floor: dict = field(default_factory=dict)
    u_floor: dict = field(default_factory=dict)
    b_floor: dict = field(default_factory=dict)
    a_wall: dict = field(default_factory=dict)
    u_wall: dict = field(default_factory=dict)
    b_wall: dict = field(default_factory=dict)
    a_door: dict = field(default_factory=dict)
    u_door: dict = field(default_factory=dict)
    a_window: dict = field(default_factory=dict)
    a_window_specific: dict = field(default_factory=dict)
    delta_u_thermal_bridging: dict = field(default_factory=dict)
    u_window: dict = field(default_factory=dict)
    g_gl_n_window: dict = field(default_factory=dict)

    def __post_init__(self):
        for field in fields(self):
            if field.name.startswith(("a_", "u_", "b_")) and isinstance(
                getattr(self, field.name), dict
            ):
                self.validate_dict_keys(getattr(self, field.name), field.name)

    def validate_dict_keys(self, dictionary, field_name):
        required_prefix = field_name + "_"

        if field_name == "a_window_specific":
            required_keys = {
                "a_window_horizontal",
                "a_window_east",
                "a_window_south",
                "a_window_west",
                "a_window_north",
            }
            actual_keys = set(dictionary.keys())
            if not required_keys.issubset(actual_keys):
                raise ValueError(
                    f"All keys in {field_name} must be one of {required_keys}"
                )
        else:
            for key in dictionary.keys():
                if not key.startswith(required_prefix):
                    raise ValueError(
                        f"All keys in {field_name} must start with {required_prefix}"
                    )

                try:
                    int_part = int(key[len(required_prefix):])
                except ValueError:
                    raise ValueError(
                        f"The numeric part of the key in {field_name} must be an integer"
                    )


class Building:
    def __init__(
        self,
        number_of_time_steps: float,
        tabula_building_code: str = None,
        country: str = None,
        class_building: str = "average",
        building_type: str = None,
        refurbishment_status="no_refurbishment",
        construction_year: int = None,
        floor_area: float = None,
        building_parameters: BuildingParameters = None,
    ):
        if building_parameters is not None:
            print(
                "You entered the Expert mode, by using a defining your own " "building"
            )
            self.tabula_building_code = tabula_building_code
        else:
            main_path = get_project_root()
            self.tabula_df = pd.DataFrame(
                pd.read_csv(
                    os.path.join(
                        main_path,
                        "thermal_building_model",
                        "tabula",
                        "tabula_data_sorted.csv",
                    ),
                    low_memory=False,
                )
            )
            if tabula_building_code is not None:
                print(
                    "You entered the Expert mode, by using a specific building"
                    "code name"
                )
                self.tabula_building_code = tabula_building_code
            else:
                self.tabula_building_code = self.define_tabula_building_code(
                    country=country,
                    building_type=building_type,
                    construction_year=construction_year,
                    refurbishment_status=refurbishment_status,
                )
        self.building_parameters = building_parameters
        self.class_building = class_building
        self.number_of_time_steps = number_of_time_steps
        if floor_area is not None:
            print(
                "You initialized a floor area, which can deviate from"
                "the floor area of the tabula buildings"
            )
            self.floor_area = floor_area
        else:
            self.floor_area = None
        # DIN 13790: 12.3.1.2
        self.list_class_buildig = {
            "very light": {"a_m_var": 2.5, "c_m_var": 80000},
            "light": {"a_m_var": 2.5, "c_m_var": 110000},
            "average": {"a_m_var": 2.5, "c_m_var": 165000},
            "heavy": {"a_m_var": 3.0, "c_m_var": 260000},
            "very heavy": {"a_m_var": 3.0, "c_m_var": 370000},
        }
        self.building_config = {}

    def define_tabula_building_code(
        self,
        country: str,
        construction_year: int,
        building_type: str,
        refurbishment_status: str,
    ):
        self.tabula_df = self.tabula_df[
            (self.tabula_df["Code_Country"] == country)
            & (self.tabula_df["Code_BuildingSizeClass"] == building_type)
            & (self.tabula_df["Code_DataType_Building"] == "ReEx")
            & (
                pd.to_numeric(self.tabula_df["Year1_Building"], errors="coerce").fillna(
                    0
                )
                <= construction_year
            )
            & (
                pd.to_numeric(self.tabula_df["Year2_Building"], errors="coerce").fillna(
                    0
                )
                >= construction_year
            )
        ]
        if refurbishment_status in {
            "no_refurbishment",
            "usual_refurbishment",
            "advanced_refurbishment",
        }:
            variant_mapping = {
                "no_refurbishment": 1,
                "usual_refurbishment": 2,
                "advanced_refurbishment": 3,
            }
            self.tabula_df = self.tabula_df[
                self.tabula_df["Number_BuildingVariant"]
                == variant_mapping[refurbishment_status]
            ]

        assert len(self.tabula_df) <= 1, (
            "More than one building is founded for "
            "the input parameters. Please write an "
            "issue in Github"
        )
        return self.tabula_df["Code_BuildingVariant"]

    def calculate_all_parameters(self):
        if self.building_parameters is not None:
            self.initialize_from_building_parameters()
        else:
            self.get_building_parameters_from_csv()
        self.total_internal_area: float = self.calc_internal_area()
        self.h_ve: float = self.calc_h_ve()
        self.h_tr_w: float = self.calc_h_tr_w()
        self.h_tr_em: float = self.calc_h_tr_em()
        self.h_tr_is: float = self.calf_h_tr_is()
        self.mass_area: float = self.calc_mass_area()
        self.h_tr_ms: float = self.calf_h_tr_ms()
        self.c_m: float = self.calc_c_m()
        # self.solar_gains : list  = self.calc_solar_gaings_through_windows()
        self.building_config = self.build_building_config()

    def build_building_config(self):
        building_config = BuildingConfig5RC(
            total_internal_area=self.total_internal_area,
            h_ve=self.h_ve,
            h_tr_w=self.h_tr_w,
            h_tr_em=self.h_tr_em,
            h_tr_is=self.h_tr_is,
            mass_area=self.mass_area,
            h_tr_ms=self.h_tr_ms,
            c_m=self.c_m,
            floor_area=self.floor_area,
            heat_transfer_coefficient_ventilation=self.heat_transfer_coefficient_ventilation,
            total_air_change_rate=self.total_air_change_rate,
        )
        return building_config

    def initialize_from_building_parameters(self):
        for field in fields(BuildingParameters):
            setattr(self, field.name, getattr(
                self.building_parameters, field.name))

    def get_building_parameters_from_csv(self):
        row = self.tabula_df.loc[
            self.tabula_df["Code_BuildingVariant"] == self.tabula_building_code
        ]

        list_type = ["", "Measure_", "Actual_"]
        t_b = list_type[1]
        self.opaque_elements = ["wall", "roof", "floor"]

        self.floor_area_reference = float(row["A_C_Ref"].values[0])
        self.calc_floor_area_ratio()
        self.a_roof = {
            "a_roof_1": float(row["A_Roof_1"].values[0]),
            "a_roof_2": float(row["A_Roof_2"].values[0]),
        }
        self.a_roof = {
            key: value * self.floor_area_ratio for key, value in self.a_roof.items()
        }
        self.u_roof = {
            "u_roof_1": float(row["U_" + str(t_b) + "Roof_1"].values[0]),
            "u_roof_2": float(row["U_" + str(t_b) + "Roof_2"].values[0]),
        }
        self.b_roof = {
            "b_roof_1": float(row["b_Transmission_Roof_1"].values[0]),
            "b_roof_2": float(row["b_Transmission_Roof_2"].values[0]),
        }
        self.a_floor = {
            "a_floor_1": float(row["A_Floor_1"].values[0]),
            "a_floor_2": float(row["A_Floor_2"].values[0]),
        }
        self.a_floor = {
            key: value * self.floor_area_ratio for key, value in self.a_floor.items()
        }
        self.u_floor = {
            "u_floor_1": float(row["U_" + str(t_b) + "Floor_1"].values[0]),
            "u_floor_2": float(row["U_" + str(t_b) + "Floor_2"].values[0]),
        }
        self.b_floor = {
            "b_floor_1": float(row["b_Transmission_Floor_1"].values[0]),
            "b_floor_2": float(row["b_Transmission_Floor_2"].values[0]),
        }

        self.a_wall = {
            "a_wall_1": float(row["A_Wall_1"].values[0]),
            "a_wall_2": float(row["A_Wall_2"].values[0]),
            "a_wall_3": float(row["A_Wall_3"].values[0]),
        }
        self.a_wall = {
            key: value * self.floor_area_ratio for key, value in self.a_wall.items()
        }
        self.u_wall = {
            "u_wall_1": float(row["U_" + str(t_b) + "Wall_1"].values[0]),
            "u_wall_2": float(row["U_" + str(t_b) + "Wall_2"].values[0]),
            "u_wall_3": float(row["U_" + str(t_b) + "Wall_3"].values[0]),
        }
        self.b_wall = {
            "b_wall_1": float(row["b_Transmission_Wall_1"].values[0]),
            "b_wall_2": float(row["b_Transmission_Wall_2"].values[0]),
            "b_wall_3": float(row["b_Transmission_Wall_3"].values[0]),
        }

        self.a_door = {"a_door_1": float(row["A_Door_1"].values[0])}
        self.a_door = {
            key: value * self.floor_area_ratio for key, value in self.a_door.items()
        }

        self.u_door = {"u_door_1": float(
            row["U_" + str(t_b) + "Door_1"].values[0])}

        self.a_window = {
            "a_window_1": float(row["A_Window_1"].values[0]),
            "a_window_2": float(row["A_Window_2"].values[0]),
        }
        self.a_window = {
            key: value * self.floor_area_ratio for key, value in self.a_window.items()
        }
        self.a_window_specific = {
            "a_window_horizontal": float(row["A_Window_Horizontal"].values[0]),
            "a_window_east": float(row["A_Window_East"].values[0]),
            "a_window_south": float(row["A_Window_South"].values[0]),
            "a_window_west": float(row["A_Window_West"].values[0]),
            "a_window_north": float(row["A_Window_North"].values[0]),
        }
        self.a_window_specific = {
            key: value * self.floor_area_ratio
            for key, value in self.a_window_specific.items()
        }
        self.delta_u_thermal_bridiging = {
            "delta_u_thermal_bridiging": float(row["delta_U_ThermalBridging"].values[0])
        }
        self.u_window = {
            "u_window_1": float(row["U_" + str(t_b) + "Window_1"].values[0]),
            "u_window_2": float(row["U_" + str(t_b) + "Window_2"].values[0]),
        }
        self.g_gl_n_window = {
            "g_gl_n_window_1": float(row["g_gl_n_Window_1"].values[0]),
            "g_gl_n_window_2": float(row["g_gl_n_Window_2"].values[0]),
        }

        self.heat_transfer_coefficient_ventilation = float(
            row["h_Ventilation"].values[0]
        )

        # References to check results
        self.q_transmission_losses_annual = float(
            row["q_ht_tr"].values[0] * self.floor_area
        )  # [kWh/a)]
        self.q_ventilation_losses_annual = float(
            row["q_ht_ve"].values[0] * self.floor_area
        )  # [kWh/a)]
        self.q_total_losses_annual = float(
            row["q_ht"].values[0])  # [kWh/(m²a)]
        self.q_solar_gains_annual = float(
            row["q_sol"].values[0])  # [kWh/(m²a)]
        self.q_internal_gains_annual = float(
            row["q_int"].values[0])  # [kWh/(m²a)]
        self.q_internal_gains_annual = float(
            row["q_int"].values[0])  # [kWh/(m²a)]
        self.total_air_change_rate = float(
            row["n_air_use"] + row["n_air_infiltration"]
        )  # [1/h]
        self.room_height = float(row["h_room"])  # [m]
        self.q_total_losses = float(row["q_ht"] * self.floor_area)  # [kWh/a]
        self.q_heating_demand_annual = float(
            row["q_h_nd"] * self.floor_area)  # [kWh/a]
        self.h_transmission = float(
            row["h_Transmission"] * self.floor_area)  # [W/K]
        self.h_ventilation = float(
            row["h_Ventilation"] * self.floor_area)  # [W/K]

    def calc_floor_area_ratio(self):
        if self.floor_area is None:
            self.floor_area = self.floor_area_reference
            self.floor_area_ratio = 1
        else:
            warnings.warn(
                "Experimental mode: The floor area is unequeal"
                "to the tabula reference floor area",
                UserWarning,
            )
            self.floor_area_ratio = self.floor_area / self.floor_area_reference
            if self.floor_area_ratio > 1:
                print(
                    "The chosen floor is "
                    + str(round((1 - self.floor_area_ratio) * 100, 3))
                    + " % "
                    "bigger than the tabula reference floor area"
                )
            elif self.floor_area_ratio < 1:
                print(
                    "The chosen floor is "
                    + str(round((1 - self.floor_area_ratio) * 100, 3))
                    + " % "
                    "smaller than the tabula reference floor area"
                )
            if 0.9 > self.floor_area_ratio or 1.1 < self.floor_area_ratio:
                warnings.warn(
                    "The chosen floor area is more than 10 % different to the "
                    "associated tabula building. It might influence "
                    "the results strong and unpredictable",
                    UserWarning,
                )

    def calc_internal_area(self):
        # DIN 7.2.2.2
        # the dimensionless ratio between the surface area of all surfaces facing into the room and the useful area.
        var_at = 4.5
        total_internal_area = self.floor_area * var_at
        return total_internal_area

    def calc_h_tr_em(self):
        h_tr_em = 0
        a_external = 0
        for x in range(1, len(self.a_wall) + 1):
            h_tr_em = (
                h_tr_em
                + self.a_wall["a_wall_" + str(x)]
                * self.u_wall["u_wall_" + str(x)]
                * self.b_wall["b_wall_" + str(x)]
            )
            a_external = a_external + self.a_wall["a_wall_" + str(x)]

        for x in range(1, len(self.a_roof) + 1):
            h_tr_em = (
                h_tr_em
                + self.a_roof["a_roof_" + str(x)]
                * self.u_roof["u_roof_" + str(x)]
                * self.b_roof["b_roof_" + str(x)]
            )
            a_external = a_external + self.a_roof["a_roof_" + str(x)]

        for x in range(1, len(self.a_floor) + 1):
            h_tr_em = (
                h_tr_em
                + self.a_floor["a_floor_" + str(x)]
                * self.u_floor["u_floor_" + str(x)]
                * self.b_floor["b_floor_" + str(x)]
            )
            a_external = a_external + self.a_floor["a_floor_" + str(x)]

        for x in range(1, len(self.a_door) + 1):
            h_tr_em = (
                h_tr_em
                + self.a_door["a_door_" +
                              str(x)] * self.u_door["u_door_" + str(x)]
            )
            a_external = a_external + self.a_door["a_door_" + str(x)]
        h_tr_em = (
            h_tr_em
            + self.delta_u_thermal_bridiging["delta_u_thermal_bridiging"] * a_external
        )
        return h_tr_em  # [W/K]

    def calc_h_tr_w(self):
        h_tr_w = 0
        a_window = 0
        for x in range(1, len(self.a_window) + 1):
            h_tr_w = (
                h_tr_w
                + self.a_window["a_window_" + str(x)]
                * self.u_window["u_window_" + str(x)]
            )
            a_window = a_window * self.a_window["a_window_" + str(x)]
        h_tr_w = (
            h_tr_w
            + self.delta_u_thermal_bridiging["delta_u_thermal_bridiging"] * a_window
        )
        return h_tr_w  # [W/K]

    def calc_h_ve(self):
        # Determine the ventilation conductance, based on DIN13790 9.3.1
        air_cap_vol_heat = (
            # volume-related heat storage capacity of the air in [J/(m^3 * K)]
            1200
        )
        total_air_change_per_hour = (
            self.total_air_change_rate * self.room_height * self.floor_area
        )  # [m^3 / h]

        h_ve = (air_cap_vol_heat / 3600) * total_air_change_per_hour  # [W/K]
        return h_ve

    def calf_h_tr_ms(self):
        h_tr_ms = 9.1 * self.mass_area
        return h_tr_ms

    def calf_h_tr_is(self):
        h_tr_is = 3.45 * self.total_internal_area
        return h_tr_is

    def calc_mass_area(self):
        # Based on ISO standard 12.3.1.2
        mass_area = (
            self.floor_area *
            self.list_class_buildig[self.class_building]["a_m_var"]
        )
        return mass_area

    def calc_c_m(self):
        # [kWh/K] Room Capacitance. Based on ISO standard 12.3.1.2
        c_m = self.floor_area * \
            self.list_class_buildig[self.class_building]["c_m_var"]
        return c_m

    def calc_solar_gaings_through_windows(self, object_location_of_building):
        a_window_total = 0
        g_gl_n_window_avg = 0
        for x in range(1, len(self.u_window) + 1):
            a_window_total = a_window_total + \
                self.a_window["a_window_" + str(x)]

        for x in range(1, len(self.g_gl_n_window) + 1):
            g_gl_n_window_avg = (
                g_gl_n_window_avg
                + (
                    self.g_gl_n_window["g_gl_n_window_" + str(x)]
                    * self.a_window["a_window_" + str(x)]
                )
                / a_window_total
            )

        compass_directions = {
            "north": {"azimuth_tilt": 270, "alititude_tilt": 90},
            "east": {"azimuth_tilt": 90, "alititude_tilt": 90},
            "south": {"azimuth_tilt": 180, "alititude_tilt": 90},
            "west": {"azimuth_tilt": 0, "alititude_tilt": 90},
            "horizontal": {"azimuth_tilt": 0, "alititude_tilt": 0},
        }
        list_solar_gains = []
        for hour in range(self.number_of_time_steps):
            sum_solar_gains = 0
            for x in compass_directions:
                (
                    altitude,
                    azimuth,
                ) = object_location_of_building.calc_sun_position(
                    latitude_deg=48.16,
                    longitude_deg=46.38,
                    year=2015,
                    hoy=hour,
                )
                azimuth_tilt = compass_directions[x]["azimuth_tilt"]
                alititude_tilt = compass_directions[x]["alititude_tilt"]
                window_var = Window(
                    azimuth_tilt=azimuth_tilt,
                    alititude_tilt=alititude_tilt,
                    glass_solar_transmittance=g_gl_n_window_avg,
                    glass_light_transmittance=0.8,
                    area=self.a_window_specific["a_window_" + str(x)],
                )

                window_var.calc_solar_gains(
                    sun_altitude=altitude,
                    sun_azimuth=azimuth,
                    normal_direct_radiation=object_location_of_building.weather_data[
                        "dirnorrad_Whm2"
                    ][hour],
                    horizontal_diffuse_radiation=object_location_of_building.weather_data[
                        "difhorrad_Whm2"
                    ][
                        hour
                    ],
                )
                sum_solar_gains = window_var.solar_gains + sum_solar_gains
            list_solar_gains.append(sum_solar_gains)
        return list_solar_gains