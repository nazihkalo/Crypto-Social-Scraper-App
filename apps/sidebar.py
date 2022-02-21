import streamlit as st
import pandas as pd
from .ui import (
    get_social_links_html,
    get_community_data,
    get_cg_summary_data,
)
import streamlit.components.v1 as components
from .utils import (
    get_one_token_latest,
    load_coingecko_data,
)


def get_sidebar():
    loading_data_container = st.sidebar.empty()
    loading_data_container.info("Loading data...")
    static_data = load_coingecko_data()
    loading_data_container.success("Loading data...done!")
    loading_data_container.empty()

    with st.sidebar:
        st.markdown("### Select which Cryptocurrency you'd like to look into!")
        coin_choice = st.selectbox("Pick a coin", static_data.name.tolist())
        st.image(
            "./images/cryptomeme.gif",
        )
        coin_id = static_data[static_data.name == coin_choice].id.values[0]
        data = get_one_token_latest(coin_id)
        # image_link = (
        #     data.loc[data.name == str(coin_choice), "image"]
        #     .values[0]
        #     .get("small", "")
        # )
        get_cg_summary_data(coin_choice, data)
        st.markdown(f"### Social Data / Links")
        # community_data = get_community_data(coin_choice, data)
        components.html(str(get_social_links_html(coin_choice, data)))
        st.markdown(
            "*Check out the app mechanics [here](https://github.com/nazihkalo/Crypto-Social-Scraper-App).*"
        )
    return {"data": data, "coin_choice": coin_choice, "coin_id": coin_id}
