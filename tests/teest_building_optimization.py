from thermal_building_model.tabula.tabula_reader import Building
from thermal_building_model.m_5RC import M5RC

from oemof.solph import views
import oemof.solph as solph


def test_building_optimization():
    #  create solver
    solver = "cbc"  # 'glpk', 'gurobi',....
    solver_verbose = False  # show/hide solver output
    number_of_time_steps = 100
    building_example = Building(
        tabula_building_code="DE.N.SFH.05.Gen.ReEx.001.002",
        class_building="average",
        number_of_time_steps=number_of_time_steps,
    )
    building_example.calculate_all_parameters()
    internal_gains = []
    t_outside = []
    solar_gains = []
    for _ in range(number_of_time_steps):
        internal_gains.append(100)
        t_outside.append(10)
        solar_gains.append(100)

    date_time_index = solph.create_time_index(
        2012, number=number_of_time_steps)
    es = solph.EnergySystem(timeindex=date_time_index,
                            infer_last_interval=False)
    # create electricity, heat and cooling flow
    b_heat = solph.buses.Bus(label="b_heat")
    es.add(b_heat)
    b_cool = solph.buses.Bus(label="b_cool")
    es.add(b_cool)
    b_elect = solph.buses.Bus(label="electricity_from_grid")
    es.add(b_elect)

    # add electricity from grid
    es.add(
        solph.components.Source(
            label="elect_from_grid",
            outputs={b_elect: solph.flows.Flow(variable_costs=30)},
        )
    )

    # add heating and cooling components
    es.add(
        solph.components.Transformer(
            label="ElectricalHeater",
            inputs={b_elect: solph.flows.Flow()},
            outputs={b_heat: solph.flows.Flow()},
            conversion_factors={b_elect: 1},
        )
    )
    es.add(
        solph.components.Transformer(
            label="ElectricalCooler",
            inputs={b_cool: solph.flows.Flow(), b_elect: solph.flows.Flow()},
            outputs={},
            conversion_factors={b_cool: 1, b_elect: 1},
        )
    )
    # add building
    es.add(
        M5RC(
            label="GenericBuilding",
            inputs={b_heat: solph.flows.Flow(variable_costs=0)},
            outputs={b_cool: solph.flows.Flow(variable_costs=0)},
            solar_gains=solar_gains,
            t_outside=t_outside,
            internal_gains=internal_gains,
            t_set_heating=20,
            t_set_cooling=30,
            building_config=building_example.building_config,
            t_inital=26,
        )
    )
    model = solph.Model(es)
    model.solve(solver=solver, solve_kwargs={"tee": solver_verbose})
    es.results["main"] = solph.processing.results(model)
    results = es.results["main"]
    assert (
        views.node(results, "GenericBuilding")["sequences"][
            (("GenericBuilding", "None"), "t_air")
        ][0]
        == 26
    )
    assert (
        views.node(results, "GenericBuilding")["sequences"][
            (("GenericBuilding", "None"), "t_air")
        ][5]
        == 22.367105
    )
    assert (
        views.node(results, "GenericBuilding")["sequences"][
            (("GenericBuilding", "None"), "t_air")
        ][9]
        == 20.403484
    )
