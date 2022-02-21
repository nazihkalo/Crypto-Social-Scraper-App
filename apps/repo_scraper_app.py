from millify import millify
import urllib.parse as urlparse
import datetime
import os
import streamlit as st
from hydralit import HydraHeadApp
from . import ui
from . import utils
from .scrapers.scrape_repo_minimal import (
    RepoScraper,
    ScrapeGithubUrl,
    UserProfileGetter,
)

# from top_github_scraper.utils import ScrapeGithubUrl, UserProfileGetter
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

USERNAME = os.getenv("GITHUB_USERNAME_LIVE")
TOKEN = os.getenv("GITHUB_TOKEN_LIVE")


class RepoScraperApp(HydraHeadApp):
    def __init__(self, title="Home App", **kwargs):
        self.__dict__.update(kwargs)
        self.title = title

    def _body(self, commit_history, git_container):

        # Get filters
        filters_container = git_container.expander("Filtering Options")
        start, end, contributor = ui.get_git_bar(commit_history, filters_container)

        # Apply filters
        contributor_stats, q_contrib = utils.get_contributor_stats(
            commit_history, contributor
        )
        commit_history = utils.filter_by_date(commit_history, start, end)
        commit_history = utils.filter_by_contributor(commit_history, contributor)
        # Top-level repository stats
        git_container.markdown(
            """
        <style>
        .small-font {
            font-size:15px;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        # Top-level repo stats
        repo_stats = utils.get_repo_stats(commit_history)
        # p1, p2 = git_container.columns([1, 1])
        with git_container.container():
            git_container.subheader("Repository Snapshot")
            markdownn = " | ".join(
                [
                    f"{stat[1][1]} **{stat[0]}**: {stat[1][0]}"
                    for stat in repo_stats.items()
                ]
            )
            git_container.markdown(markdownn, unsafe_allow_html=True)
            try:
                git_container.subheader(
                    f"Contributor: {contributor_stats.pop('Contributor')[0]}"
                )
                for c_stat in contributor_stats.items():
                    git_container.markdown(
                        f"<p class='small-font'>{c_stat[1][1]} <strong>{c_stat[0]}</strong>: {c_stat[1][0]}</p>",  # noqa: E501
                        unsafe_allow_html=True,
                    )
                git_container.write(ui.plot_quarterly_commits(q_contrib))
            except (AttributeError, KeyError):
                pass

        git_container.markdown("---")
        git_container.write(ui.plot_commit_waffle(commit_history))
        with git_container.expander("Changes Overview", expanded=True):
            git_container.write(ui.plot_daily_contributions(commit_history))
            git_container.write(ui.plot_inserts_deletions(commit_history))

        with git_container.expander("Contributors Overview", expanded=True):
            git_container.write(
                ui.plot_top_contributors(utils.get_top_contributors(commit_history))
            )
            git_container.write(
                ui.plot_cumulative_lines_by_contributor(commit_history, 30)
            )

    # This one method that must be implemented in order to be used in a Hydralit application.
    # The application must also inherit from the hydrapp class in order to correctly work within Hydralit.
    def run(self):
        try:
            data = self.__dict__["data"]
            coin_choice = self.__dict__["coin_choice"]

            repo_link_choice = data.loc[
                data.name == coin_choice, "github_repos_complete"
            ].values[0]
            repo_choice = st.selectbox("Select a repo", repo_link_choice)
            repo_scraper = RepoScraper(
                [""], max_n_top_contributors=100, USERNAME=USERNAME, TOKEN=TOKEN
            )
            repo_path = urlparse.urlparse(repo_choice).path
            repo_important_info = repo_scraper._get_repo_information(repo_path)
            contributors_info = repo_scraper._get_contributor_repo_of_one_repo(
                repo_path
            )

            repo_info_df = pd.DataFrame([repo_important_info])
            contributors_info_df = pd.DataFrame.from_records(contributors_info)
            user_getter = UserProfileGetter(contributors_info_df.url.tolist())
            users_df = user_getter.get_all_user_profiles()

            contributors_users_merged_df = pd.merge(
                contributors_info_df, users_df, on="login"
            )
            keep_cols = [
                col for col in contributors_users_merged_df.columns if not "url" in col
            ]
            contributors_info_df_styled = (
                contributors_users_merged_df[keep_cols]
                .style.format(
                    {
                        "contributions": lambda x: f"{millify(x)}",
                    }
                )
                .bar(
                    subset=[
                        "contributions",
                    ],
                    color="#a69232",
                )
            )

            # st.dataframe(repo_info_df)
            # st.dataframe(contributors_info_df)
            st.dataframe(contributors_info_df_styled)

            # st.dataframe(users_df)
            # st.write(users_df.columns)

            input_type = st.radio(
                "Filter Repo Commits",
                (
                    "Filter commits by Date",
                    "Filter commits by n",
                    "Don't filter commits (large repos make take time)",
                ),
            )

            if input_type == "Filter commits by Date":
                filter_option = st.date_input(
                    "Pulling repository commits from: (default 2021-01-01)",
                    datetime.date(2021, 1, 1),
                )
                d = datetime.datetime.combine(
                    filter_option, datetime.datetime.min.time()
                )
            elif input_type == "Filter commits by n":
                filter_option = st.number_input(
                    "Pull the first `n` commits", min_value=1, max_value=None, value=100
                )
            elif input_type == "Filter commits by n":
                filter_option = None
            git_container = st.empty()
            with git_container:
                git_container.title("Git Repository Overview")
                second_container = git_container.container()
                with st.form(key="my_form_to_submit"):
                    submit_button = st.form_submit_button(label="Submit")
                    if submit_button:
                        if input_type == "Filter commits by Date":
                            commit_history = utils.get_repo_data(
                                repo_choice, since=d
                            )  # d.strftime("%Y-%m-%d")
                        elif input_type == "Filter commits by n":
                            commit_history = utils.get_repo_data(
                                repo_choice, first_n_commits=filter_option
                            )

                        body = self._body(commit_history, second_container)
        except Exception as e:
            st.image(
                os.path.join(".", "images", "failure.png"),
                width=100,
            )
            st.error(
                "An error has occurred, someone will be punished for your inconvenience, we humbly request you try again."
            )
            st.error("Error details: {}".format(e))
