import datetime
import os
import streamlit as st
from hydralit import HydraHeadApp

MENU_LAYOUT = [1, 1, 1, 7, 2]
import pandas as pd

# from sqlalchemy import true
import streamlit as st
import json
from .ui import (
    get_repo_stats_aggregates,
    get_repo_stats_history,
    plot_coin_stats,
    plot_stargazers_by_repo,
    plot_lines_stats,
    plot_total_commits_,
)
import streamlit.components.v1 as components
from .utils import (
    get_description,
    get_one_token_latest_market_data,
    get_subgraph_info,
)
from pathlib import Path


class MainApp(HydraHeadApp):
    def __init__(self, title="Home App", **kwargs):
        self.__dict__.update(kwargs)
        self.title = title

    # This one method that must be implemented in order to be used in a Hydralit application.
    # The application must also inherit from the hydrapp class in order to correctly work within Hydralit.
    def run(self):

        try:

            ### LOAD DATA
            data = self.__dict__["data"]
            coin_choice = self.__dict__["coin_choice"]
            coin_id = self.__dict__["coin_id"]

            left_col, right_col = st.columns(2)

            image_link = (
                data.loc[data.name == str(coin_choice), "image"]
                .values[0]
                .get("small", "")
            )
            ### Description
            description_text = get_description(data, coin_choice)
            st.markdown(f"# {coin_choice} ![]({image_link})")
            lef_expander1 = st.expander("Coin Description")

            with lef_expander1:
                st.markdown(description_text, unsafe_allow_html=True)
            ## HIGH LEVEL STATS

            left_col, right_col = st.columns(2)
            chart_data = get_repo_stats_history(coin_choice, data)
            market_data = get_one_token_latest_market_data(coin_id)
            # st.dataframe(market_data)
            with right_col:
                st.markdown("### Price Over Time")
                st.altair_chart(
                    plot_coin_stats(market_data),
                    use_container_width=True,
                )

            if len(chart_data) > 0:
                with left_col:
                    st.markdown("### Github Repo Lines & Commits over Time")

                    st.altair_chart(
                        plot_lines_stats(chart_data),
                        use_container_width=True,
                    )
                    st.altair_chart(
                        plot_total_commits_(chart_data),
                        use_container_width=True,
                    )
                st.markdown("### Github Repo Stargazer counts over Time")
                st.altair_chart(
                    plot_stargazers_by_repo(chart_data), use_container_width=True
                )

            else:
                st.write("No repo info found.")
            st.markdown("### Github Repo Stats Aggregated")
            get_repo_stats_aggregates(coin_choice, data)
        except Exception as e:
            st.image(
                os.path.join(".", "images", "failure.png"),
                width=100,
            )
            st.error(
                "An error has occurred, someone will be punished for your inconvenience, we humbly request you try again."
            )
            st.error("Error details: {}".format(e))
