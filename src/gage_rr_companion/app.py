from __future__ import annotations

import json
import pandas as pd
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

from gage_rr_companion.compute import ComputeGageRR
from gage_rr_companion.gage_rr_io import load_gage_rr_data


app_ui = ui.page_fluid(
    ui.h2("Gage R&R Companion"),
    ui.input_file(
        "data",
        "Upload your Gage R&R data (CSV format)",
        accept=[".csv"],
        multiple=False,
    ),
    ui.hr(),
    ui.output_ui("results_ui"),
)


def server(input: Inputs, output: Outputs, session: Session):

    @reactive.calc
    def results():
        files = input.data()
        if not files:
            return None

        path = files[0]["datapath"]  # temp file on disk
        df = load_gage_rr_data(path, is_path=True)
        return ComputeGageRR(df)

    @output
    @render.ui
    def results_ui():
        res = results()
        if res is None:
            return ui.p("Upload a CSV to see results.")

        return ui.TagList(
            ui.h4("ANOVA Table"),
            ui.output_data_frame("anova_tbl"),

            ui.h4("Variance Components"),
            ui.output_data_frame("var_tbl"),

            ui.h4("Gage R&R Table"),
            ui.output_data_frame("grr_tbl"),

            ui.h4("Operator Statistics"),
            ui.output_data_frame("ops_tbl"),

            ui.h4("Summary Metrics"),
            ui.output_text_verbatim("summary_json"),
        )

    @output
    @render.data_frame
    def anova_tbl():
        res = results()
        return render.DataGrid(res["anova_table"]) if res else render.DataGrid(pd.DataFrame())

    @output
    @render.data_frame
    def var_tbl():
        res = results()
        return render.DataGrid(res["variance_components"]) if res else render.DataGrid(pd.DataFrame())

    @output
    @render.data_frame
    def grr_tbl():
        res = results()
        return render.DataGrid(res["gage_rr_table"]) if res else render.DataGrid(pd.DataFrame())

    @output
    @render.data_frame
    def ops_tbl():
        res = results()
        return render.DataGrid(res["operator_stats"]) if res else render.DataGrid(pd.DataFrame())

    @output
    @render.text
    def summary_json():
        res = results()
        return "" if not res else json.dumps(res.get("summary_metrics", {}), indent=2)


app = App(app_ui, server)