import altair as alt
import pandas as pd
import streamlit as st
from pandas.tseries import offsets

import utils



### SUmmary stats from coingecko

def get_cg_summary_data(coin_choice, df):
       summary_cols = ['genesis_date',    
       'market_cap_rank', 
       'sentiment_votes_up_percentage',
       'sentiment_votes_down_percentage', 
       'coingecko_rank',
       'coingecko_score', 
       'developer_score', 
       'community_score',
       'liquidity_score', 
       'public_interest_score', 
       'last_updated', 
       'contract_address']
       cg_data = df.loc[df.name == coin_choice,summary_cols]
       for col in cg_data.columns:
              st.markdown(
              f"<p class='small-font'><strong>{col}</strong>: {cg_data[col].values[0]}</p>",  # noqa: E501
              unsafe_allow_html=True,
              )

##### Market Data
def get_market_data(coin_choice, df):
    market_data_json = df.loc[df.name == coin_choice,'market_data'][0]
    market_cap = market_data_json['market_cap']
    current_price = market_data_json['current_price']
    circulating_supply = market_data_json['circulating_supply']
    price_change_percentage_24h = market_data_json['market_cap_change_percentage_24h_in_currency']
    # text = f"#### Market Cap {market_cap['usd']}\n#### Total Supply {circulating_supply}\n#### Current Price {current_price['usd']}\n#### Price Change 24h {price_change_percentage_24h['usd']}\n"
    market_stats = {"market_cap" : (f"${market_cap['usd']:,}", "💰"), 
        'current_price':(f"${current_price['usd']:,}", "🤑"),
        'circulating_supply':(f"{circulating_supply:,}", "💩"),
        'price_change_percentage_24h':(f"{price_change_percentage_24h['usd']:.0%}", "%")}
    return market_stats

####### SOCIALS

def get_community_data(coin_choice, df):
    market_data_json = df.loc[df.name == coin_choice,'community_data'][0]
    market_data_json = {k:v if v else 0 for (k,v) in market_data_json.items()}
    resp = {"Facebook Likes": (f"{market_data_json['facebook_likes']:,}", "💬"),
            "Twitter Followers": (f"{market_data_json['twitter_followers']:,}", "💬"),
            "Reddit Average posts 48h": (f"{market_data_json['reddit_average_posts_48h']:,}", "💬"),
            "Reddit Average Comments 48h": (f"{market_data_json['reddit_average_comments_48h']:,}", "💬"),
            "Reddit Subscribers": (f"{market_data_json['reddit_subscribers']:,}", "💬"),
            "Reddit Accounts Active 48h": (f"{market_data_json['reddit_accounts_active_48h']:,}", "💬"),
            "Telegram User Count": (f"{market_data_json['telegram_channel_user_count']:,}", "💬"),}
    return resp


def get_social_links_data(coin_choice, df):
    """Gets Social media links from coingecko df"""
    links_json = df.loc[df.name == coin_choice,'links'][0]
    homepage = links_json.get("homepage")[0]
    twitter_screen_name = links_json.get("twitter_screen_name")
    twitter_link = f"https://twitter.com/{twitter_screen_name}"
    subreddit_url = links_json.get("subreddit_url")
    gitlinks = links_json.get("repos_url").get("github", [''])
    google = f"https://www.google.com/search?q={coin_choice}"
    return {'twitter':twitter_screen_name, 'github':gitlinks,'reddit':subreddit_url,'homepage':homepage, 'google':google}

def get_social_links_html(coin_choice, df):
    """Produces HTML for UI: Social media links from coingecko df"""
    HtmlFile = open("./components/social_links.html", 'r', encoding='utf-8')
    source_code = HtmlFile.read() 
    links_dict = get_social_links_data(coin_choice, df)
    github_html = ''.join([f'<a href={link} class ="fa fa-github"></a>' for link in links_dict["github"]])
    links_html = f'<body><a href="{links_dict["homepage"]}" class="fa fa-rss"></a><a href="{links_dict["twitter"]}" class="fa fa-twitter"></a><a href="{links_dict["google"]}" class="fa fa-google"></a><a href="{links_dict["reddit"]}" class="fa fa-reddit"></a>{github_html}</body></html>'
    return '</html> '+ source_code + links_html


######## GITHUB
def get_git_bar(data, container):
    
    with container:
        st.write(plot_cum_commits(data))
        contributors = data["author"].unique().tolist()
        contributors.insert(0, None)  # Manually add default

        # Filters
        contributor = st.selectbox("Select Contributor", contributors, index=0)
        start = st.date_input("Start Date", value=min(data["committed_on"]))
        end = st.date_input("End Date", value=max(data["committed_on"]))

        # Data download button
        if st.button("Download Data"):
            download_url = utils.download_data(data)
            st.markdown(download_url, unsafe_allow_html=True)

        return start, end, contributor


def get_repo_source():
    """Gets repo path (remote or uploaded file) and displays relevant UI"""
    input_type = st.sidebar.radio(
        "Input type input (.json/repo link)", ("Local .json", "Repo Link")
    )

    if input_type == "Local .json":
        repo_source = st.sidebar.file_uploader("Add your file here")
    elif input_type == "Repo Link":
        repo_source = st.sidebar.text_input("Add repo URL here", key="repo_url")

    return repo_source


def plot_top_contributors(data):
    """Plots top n contributors in a vertical histogram"""
    bars = (
        alt.Chart(data[:30])
        .mark_bar()
        .encode(
            x=alt.X("n_commits", title="N. Commits"),
            y=alt.Y("author", sort="-x", title=""),
            tooltip=[
                alt.Tooltip("author", title="Author"),
                alt.Tooltip("n_commits", title="N. Commits", format=",.0f"),
            ],
        )
        .properties(width=850, height=430, title="Top 30 Contributors")
    )

    text = bars.mark_text(align="left", baseline="middle", dx=3).encode(
        text="n_commits:Q"
    )
    return bars + text


def plot_daily_contributions(data):
    """Plots daily commits in a bar chart"""
    agg = (
        data.groupby(pd.Grouper(key="committed_on", freq="1D"))["hash"]
        .count()
        .reset_index()
    )

    plot = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("committed_on", title="Date"),
            y=alt.Y("hash", title="Commits", axis=alt.Axis(grid=False)),
            tooltip=[
                alt.Tooltip("committed_on", title="Date"),
                alt.Tooltip("hash", title="Commits"),
            ],
        )
        .properties(height=170, width=850, title="Daily Changes")
    )
    return plot


def plot_inserts_deletions(data):
    """Plots daily lines added/deleted in a bar chart"""
    agg = data.copy()
    agg["lines_deleted"] = -agg["lines_deleted"]
    agg = (
        agg.groupby(pd.Grouper(key="committed_on", freq="1D"))[
            ["lines_added", "lines_deleted"]
        ]
        .sum()
        .reset_index()
        .melt(id_vars="committed_on")
    )

    plot = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("committed_on", title="Date"),
            y=alt.Y("value", title=""),
            color=alt.condition(
                alt.datum.value > 0, alt.value("green"), alt.value("red")
            ),
            tooltip=[
                alt.Tooltip("committed_on", title="Date"),
                alt.Tooltip("value", title="Lines Changed", format=",.0f"),
                alt.Tooltip("variable"),
            ],
        )
    ).properties(height=170, width=850, title="Daily Lines Added/Removed")

    return plot


def plot_cum_commits(data):
    """Plots cumulative commits for sidebar plot"""
    added_commits_cumsum = (
        data.groupby(pd.Grouper(key="committed_on", freq="1D"))["hash"]
        .count()
        .reset_index()
        .groupby(pd.Grouper(key="committed_on", freq="1M"))
        .sum()
        .cumsum()
        .reset_index()
    )

    plot = (
        alt.Chart(added_commits_cumsum)
        .mark_area()
        .encode(
            x=alt.X("committed_on:T", title="", axis=alt.Axis(labels=False)),
            y=alt.Y("hash:Q", title="", axis=alt.Axis(labels=False)),
            tooltip=[
                alt.Tooltip("committed_on", title="Date"),
                alt.Tooltip("hash", title="Commits", format=",.0f"),
            ],
        )
        .properties(width=300, height=100)
        .configure_axis(grid=False)
    )

    return plot


def plot_commit_waffle(data):
    """Plots waffle-charte (github-like) with commits by dow/week"""
    daily_commits = (
        data.groupby(pd.Grouper(key="committed_on", freq="1D"))["hash"]
        .count()
        .reset_index()
    )
    daily_commits = daily_commits.set_index("committed_on")

    min_date = min(daily_commits.index) - offsets.YearBegin()
    max_date = max(daily_commits.index) + offsets.YearEnd()
    # Reindex by date
    idx = pd.date_range(min_date, max_date)
    daily_commits = daily_commits.reindex(idx, fill_value=0)
    daily_commits = daily_commits.rename_axis("committed_on").reset_index()
    # Add year and week to dataframe
    daily_commits["week"] = daily_commits["committed_on"].dt.isocalendar().week
    daily_commits["year"] = daily_commits["committed_on"].dt.year
    max_year = daily_commits["year"].max()

    # Year dropdown
    years = list(daily_commits["year"].unique())
    year_dropdown = alt.binding_select(options=years)
    selection = alt.selection_single(
        fields=["year"], bind=year_dropdown, name="Year", init={"year": max_year}
    )

    plot = (
        alt.Chart(daily_commits)
        .mark_rect()
        .encode(
            x=alt.X("week:O", title="Week"),
            y=alt.Y("day(committed_on):O", title=""),
            color=alt.Color(
                # FIXME: settings scales like this might lead to potential problems in
                #   some cases. Ideally, we'd need to recompute scales each time the
                #   upper bound each and every interaction.
                #   (https://stackoverflow.com/questions/68329301/fix-scale-botttom-colour-on-0-in-altair)  # noqa: E501
                "hash:Q",
                scale=alt.Scale(range=["transparent", "green"]),
                title="Commits",
            ),
            tooltip=[
                alt.Tooltip("committed_on", title="Date"),
                alt.Tooltip("day(committed_on)", title="Day"),
                alt.Tooltip("hash", title="Commits"),
            ],
        )
        .add_selection(selection)
        .transform_filter(selection)
        .properties(width=1000, height=200)
    )

    return plot


def plot_cumulative_lines_by_contributor(data, n=20):
    """Plots cumulative lines by contributor"""
    top_n = (
        data.groupby("author")["hash"]
        .count()
        .sort_values(ascending=False)[:n]
        .index.tolist()
    )

    df_top_n_month = (
        data[data["author"].isin(top_n)]
        .groupby(["author", pd.Grouper(key="committed_on", freq="M")])["lines_added"]
        .sum()
        .reset_index()
    )

    min_month = df_top_n_month["committed_on"].min()
    max_month = df_top_n_month["committed_on"].max()

    idx = pd.MultiIndex.from_product(
        [pd.date_range(min_month, max_month, freq="M"), df_top_n_month["author"].unique()]
    )
    df_top_n_month = df_top_n_month.set_index(["committed_on", "author"])
    df_top_n_month = df_top_n_month["lines_added"].reindex(idx, fill_value=0).to_frame()
    df_top_n_month = df_top_n_month.rename_axis(["committed_on", "author"]).reset_index()
    # Cumulative df
    df_top_n_month = (
        df_top_n_month.groupby(["author", "committed_on"])["lines_added"]
        .sum()
        .groupby(level=0)
        .cumsum()
        .reset_index()
    )

    selection = alt.selection_single(on="mouseover")

    plot = (
        alt.Chart(df_top_n_month)
        .mark_area()
        .encode(
            x=alt.X("committed_on", title=""),
            y=alt.Y("lines_added", title="Lines Added"),
            color=alt.condition(selection, "author", alt.value("lightgray"), legend=None),
            tooltip=[
                alt.Tooltip("committed_on"),
                alt.Tooltip("lines_added", format=",.0f"),
                alt.Tooltip("author"),
            ],
        )
        .properties(
            width=800, height=350, title=f"Cumulative Lines Added by top-{n} Contributors"
        )
        .add_selection(selection)
    )

    return plot


def plot_quarterly_commits(data):
    """Plots n_commits aggregated by quarter"""
    plot = (
        alt.Chart(data)
        .mark_area()
        .encode(
            x=alt.X("committed_on", title=""),
            y=alt.Y("hash", title="Commits"),
            tooltip=[
                alt.Tooltip("committed_on", title="Date"),
                alt.Tooltip("hash", format=",.0f", title="Commits"),
            ],
        )
        .properties(width=500, height=130)
    )

    return plot