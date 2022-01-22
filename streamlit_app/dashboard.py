import streamlit as st
from . import ui
from .ui import get_git_bar
from . import utils
from pathlib import Path


def body(commit_history, git_container):

    # Get filters
    filters_container = git_container.expander("Filtering Options")
    start, end, contributor = get_git_bar(commit_history, filters_container)

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
            [f"{stat[1][1]} **{stat[0]}**: {stat[1][0]}" for stat in repo_stats.items()]
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
        git_container.write(ui.plot_cumulative_lines_by_contributor(commit_history, 30))
