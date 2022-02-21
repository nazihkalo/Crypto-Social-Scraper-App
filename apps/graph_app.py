import os
import streamlit as st
from hydralit import HydraHeadApp

import streamlit.components.v1 as components
from .utils import (
    get_subgraph_info,
)
from pathlib import Path


class GraphApp(HydraHeadApp):
    def __init__(self, title="Home App", **kwargs):
        self.__dict__.update(kwargs)
        self.title = title

    # This one method that must be implemented in order to be used in a Hydralit application.
    # The application must also inherit from the hydrapp class in order to correctly work within Hydralit.
    def run(self):

        try:

            ### LOAD DATA
            coin_choice = self.__dict__["coin_choice"]

            st.markdown(
                "<h2>Github Repository Graph Network</h2> \
                <div>The Graph below represents the developer overlap between different tokens/ecosystems. \
                The nodes are made up of the repositories associated with the parent token/ecosystem & the edges measure the number of shared developers between the ecosystems.</div> ",
                unsafe_allow_html=True,
            )
            selector = st.select_slider(
                "Select number of neigboring tokens",
                value=10,
                options=list(range(2, 50, 1)),
            )
            with st.empty():
                get_subgraph_info(coin_choice, n=selector)

        except Exception as e:
            st.image(
                os.path.join(".", "images", "failure.png"),
                width=100,
            )
            st.error(
                "An error has occurred, someone will be punished for your inconvenience, we humbly request you try again."
            )
            st.error("Error details: {}".format(e))
