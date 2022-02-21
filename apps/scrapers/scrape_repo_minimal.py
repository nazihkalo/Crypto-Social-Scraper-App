import json
import os
from pathlib import Path
import time
from typing import List

import pandas as pd
import requests
from dotenv import load_dotenv
from rich import print
from rich.progress import track
from tqdm import tqdm
from top_github_scraper.utils import ScrapeGithubUrl, UserProfileGetter, isnotebook
import logging
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from github import Github
from ratelimit import limits
import requests

# get the standard UTC time
# g = Github(TOKEN)
# current_timezone = pytz.timezone('US/Pacific')
# reset_timestamp = g.get_rate_limit().core.reset.astimezone(current_timezone)
# sleep_time = (reset_timestamp - datetime.now(current_timezone)).seconds + 5


repo_list_file = "data/merged_repos.csv"


ONE_HOUR = 3600


class RepoScraper:
    """Scrape information of repos and the
    contributors of those repositories"""

    def __init__(
        self, repo_urls: list, max_n_top_contributors: int, USERNAME: str, TOKEN: str
    ):
        self.repo_urls = repo_urls
        self.max_n_top_contributors = max_n_top_contributors
        self.USERNAME = USERNAME
        self.TOKEN = TOKEN
        self.github = Github(TOKEN)

    @limits(calls=5000, period=ONE_HOUR)
    def call_api(self, url, *args):
        response = requests.get(url, auth=(self.USERNAME, self.TOKEN))
        # if response.status_code == 404:
        #     return "Not Found"
        # if response.status_code != 200:
        #     raise Exception("API response: {}".format(response.status_code))
        return response

    # This method is used to limit the rate of requests sent to GitHub

    def __choke(self):
        if self.github.get_rate_limit().core.remaining < 3:
            naptime = (
                self.github.get_rate_limit().core.reset - datetime.now()
            ).seconds + 5
            print(f"About to exceed rate limit :/ sleeping for {naptime} seconds")
            time.sleep(naptime)
            print("Done sleeping - back to work!")

    def get_all_top_repo_information(self):
        top_repo_infos = []

        if isnotebook():
            for repo_url in tqdm(
                self.repo_urls, desc="Scraping top GitHub repositories..."
            ):
                top_repo_infos.append(self._get_repo_information(repo_url))
        else:
            for repo_url in track(
                self.repo_urls, description="Scraping top GitHub repositories..."
            ):
                top_repo_infos.append(self._get_repo_information(repo_url))
        print(f"Finished getting repo info for {len(self.repo_urls)} repos!")
        return top_repo_infos

    def _get_repo_information(self, repo_url: str):
        self.__choke()
        repo_info_url = f"https://api.github.com/repos{repo_url}"
        repo_important_info = {}
        try:
            repo_resp = self.call_api(repo_info_url)
            repo_info = repo_resp.json()
            info_to_scrape = [
                "created_at",
                "updated_at",
                "pushed_at",
                "size",
                "stargazers_count",
                "watchers_count",
                "language",
                "has_issues",
                "has_projects",
                "has_downloads",
                "has_wiki",
                "has_pages",
                "forks_count",
            ]

            repo_important_info["repo"] = repo_url
            for info in info_to_scrape:
                repo_important_info[info] = repo_info.get(info, None)
            repo_important_info[
                "contributors"
            ] = self._get_contributor_repo_of_one_repo(repo_url)
            return repo_important_info
        except Exception as e:
            print(
                f"Request for {repo_url} failed due to {e} - status code {repo_resp.status_code}"
            )
            repo_important_info["repo"] = repo_url
            for info in info_to_scrape:
                repo_important_info[info] = "Invalid Repo"
            repo_important_info["contributors"] = "Invalid Repo"
            return repo_important_info

    def _get_contributor_repo_of_one_repo(self, repo_url: str):
        self.__choke()
        contributor_url = f"https://api.github.com/repos{repo_url}/contributors"
        contributor_page_resp = self.call_api(contributor_url)
        contributor_page = contributor_page_resp.json()
        contributors_info = {"login": [], "url": [], "contributions": []}
        try:
            max_n_top_contributors = self._find_max_n_top_contributors(
                num_contributors=len(contributor_page)
            )
            n_top_contributor = 0

            while n_top_contributor < max_n_top_contributors:
                contributor = contributor_page[n_top_contributor]

                self._get_contributor_general_info(contributors_info, contributor)
                n_top_contributor += 1

            return contributors_info
        except Exception as e:
            print(contributor_page)
            print(
                f"Failed to retrieve top contributors for {repo_url} due to {e} - status code {contributor_page_resp.status_code}"
            )
            return contributors_info

    @staticmethod
    def _get_contributor_general_info(contributors_info: List[dict], contributor: dict):

        contributors_info["login"].append(contributor["login"])
        contributors_info["url"].append(contributor["url"])
        contributors_info["contributions"].append(contributor["contributions"])

    def _find_max_n_top_contributors(self, num_contributors: int):
        if num_contributors > self.max_n_top_contributors:
            return self.max_n_top_contributors
        else:
            return num_contributors


class RepoStatsScraper:
    """Scrape information of repos and the
    contributors of those repositories"""

    def __init__(self, USERNAME: str, TOKEN: str, since: datetime = None):
        self.USERNAME = USERNAME
        self.TOKEN = TOKEN
        self.github = Github(TOKEN)
        self.since = since

    # This method is used to limit the rate of requests sent to GitHub
    def __choke(self):
        remaining = self.github.get_rate_limit().core.remaining
        print(f"There are {remaining} remaining requests before ratelimiting")
        if remaining < 3:
            naptime = (
                self.github.get_rate_limit().core.reset - datetime.now()
            ).seconds + 5
            print(f"About to exceed rate limit :/ sleeping for {naptime} seconds")
            time.sleep(naptime)
            print("Done sleeping - back to work!")

    def _get_repo_weekly_stats(self, repo_url: str):
        self.__choke()
        try:
            if repo_url.startswith("/"):
                repo_url = repo_url[1:]
            repo = self.github.get_repo(repo_url, lazy=False)

            starPages = [
                (stargazer.user.login, stargazer.starred_at)
                for stargazer in repo.get_stargazers_with_dates()
            ]
            # statsContributorsPages = repo.get_stats_contributors()
            statsCommitActivityPages = [
                week.raw_data for week in repo.get_stats_commit_activity()
            ]
            statsCodeFrequencyPages = [
                week.raw_data for week in repo.get_stats_code_frequency()
            ]

            # Stars over time
            if len(starPages) > 0:
                stargazer_dates_df = pd.DataFrame(starPages).rename(
                    columns={0: "stargazer", 1: "starred_at"}
                )
                stars_by_day = stargazer_dates_df.groupby(
                    pd.Grouper(key="starred_at", freq="1W")
                ).agg(
                    {
                        "stargazer": [list, "size"],
                    }
                )  # stargazer_dates_df.groupby(stargazer_dates_df.starred_at.dt.date).agg({'stargazer':[list, 'size'], })
                stars_by_day.columns = [i + "_" + y for i, y in stars_by_day.columns]
                stars_by_day.reset_index(inplace=True)
                stars_by_day["starred_at"] = pd.to_datetime(stars_by_day.starred_at)
            else:
                stars_by_day = pd.DataFrame(
                    columns=[
                        "starred_at",
                        "stargazer_list",
                        "stargazer_size",
                    ]
                )

            ### Commit Frequency
            if len(statsCommitActivityPages) > 0:
                statsCommitActivity_df = pd.DataFrame(statsCommitActivityPages).rename(
                    columns={"total": "total_commits", "days": "commits_per_day"}
                )
                statsCommitActivity_df["week"] = pd.to_datetime(
                    statsCommitActivity_df.week, unit="s"
                )
            else:
                statsCommitActivity_df = pd.DataFrame(
                    columns=[
                        "week",
                        "total_commits",
                        "commits_per_day",
                    ]
                )

            ### Code frequency
            if len(statsCodeFrequencyPages) > 0:
                statsCodeFrequencyPages_df = pd.DataFrame(statsCodeFrequencyPages)
                statsCodeFrequencyPages_df.rename(
                    columns={0: "week", 1: "additions", 2: "deletions"}, inplace=True
                )
                statsCodeFrequencyPages_df["week"] = pd.to_datetime(
                    statsCodeFrequencyPages_df.week, unit="s"
                )
            else:
                statsCodeFrequencyPages_df = pd.DataFrame(
                    columns=["week", "additions", "deletions"]
                )

            # merge data
            commits_add_delete_df = pd.merge(
                statsCodeFrequencyPages_df,
                statsCommitActivity_df,
                left_on="week",
                right_on="week",
                how="outer",
            )
            commits_add_delete_and_stars_df = pd.merge(
                stars_by_day,
                commits_add_delete_df,
                left_on="starred_at",
                right_on="week",
                how="outer",
            )
            commits_add_delete_and_stars_df["repo_path"] = repo_url
            return commits_add_delete_and_stars_df
        except Exception as e:
            print(f"Request for {repo_url} failed due to {e}")
            return pd.DataFrame(
                columns=[
                    "starred_at",
                    "stargazer_list",
                    "stargazer_size",
                    "week",
                    "additions",
                    "deletions",
                    "total_commits",
                    "commits_per_day",
                    "repo_path",
                ]
            )

    def _get_repo_weekly_stats_from_date(self, repo_url: str, from_datetime):
        self.__choke()
        # from_datetime = datetime.strptime('2022-01-30', '%Y-%m-%d')
        # from_datetime = datetime.strptime(since, '%Y-%m-%d')
        try:
            if repo_url.startswith("/"):
                repo_url = repo_url[1:]
            repo = self.github.get_repo(repo_url, lazy=False)

            # Get reversed order
            starPages = []
            statsCommitActivityPages = []
            statsCodeFrequencyPages = []
            stargazersPaginated = repo.get_stargazers_with_dates().reversed
            # commitActivityPaginated = reversed(repo.get_stats_commit_activity()[-1].weeks)
            # codeFrequencyPaginated = reversed(repo.get_stats_code_frequency()[-1].weeks)
            commitActivityPaginated = reversed(repo.get_stats_commit_activity())
            codeFrequencyPaginated = reversed(repo.get_stats_code_frequency())

            # Only get new info
            for stargazer in stargazersPaginated:
                if stargazer.starred_at > from_datetime:
                    starPages.append((stargazer.user.login, stargazer.starred_at))
                else:
                    break

            for week in commitActivityPaginated:
                if week.week > from_datetime:
                    statsCommitActivityPages.append(week.raw_data)
                else:
                    break

            for week in codeFrequencyPaginated:
                if week.week > from_datetime:
                    statsCodeFrequencyPages.append(week.raw_data)
                else:
                    break

            # Stars over time
            if len(starPages) > 0:
                stargazer_dates_df = pd.DataFrame(starPages).rename(
                    columns={0: "stargazer", 1: "starred_at"}
                )
                stars_by_day = stargazer_dates_df.groupby(
                    pd.Grouper(key="starred_at", freq="1W")
                ).agg(
                    {
                        "stargazer": [list, "size"],
                    }
                )  # stargazer_dates_df.groupby(stargazer_dates_df.starred_at.dt.date).agg({'stargazer':[list, 'size'], })
                stars_by_day.columns = [i + "_" + y for i, y in stars_by_day.columns]
                stars_by_day.reset_index(inplace=True)
                stars_by_day["starred_at"] = pd.to_datetime(stars_by_day.starred_at)
            else:
                stars_by_day = pd.DataFrame(
                    columns=[
                        "starred_at",
                        "stargazer_list",
                        "stargazer_size",
                    ]
                )

            ### Commit Frequency
            if len(statsCommitActivityPages) > 0:
                statsCommitActivity_df = pd.DataFrame(statsCommitActivityPages).rename(
                    columns={"total": "total_commits", "days": "commits_per_day"}
                )
                statsCommitActivity_df["week"] = pd.to_datetime(
                    statsCommitActivity_df.week, unit="s"
                )
            else:
                statsCommitActivity_df = pd.DataFrame(
                    columns=[
                        "week",
                        "total_commits",
                        "commits_per_day",
                    ]
                )

            ### Code frequency
            if len(statsCodeFrequencyPages) > 0:
                statsCodeFrequencyPages_df = pd.DataFrame(statsCodeFrequencyPages)
                statsCodeFrequencyPages_df.rename(
                    columns={0: "week", 1: "additions", 2: "deletions"}, inplace=True
                )
                statsCodeFrequencyPages_df["week"] = pd.to_datetime(
                    statsCodeFrequencyPages_df.week, unit="s"
                )
            else:
                statsCodeFrequencyPages_df = pd.DataFrame(
                    columns=["week", "additions", "deletions"]
                )

            # merge data
            commits_add_delete_df = pd.merge(
                statsCodeFrequencyPages_df,
                statsCommitActivity_df,
                left_on="week",
                right_on="week",
                how="outer",
            )
            commits_add_delete_and_stars_df = pd.merge(
                stars_by_day,
                commits_add_delete_df,
                left_on="starred_at",
                right_on="week",
                how="outer",
            )
            commits_add_delete_and_stars_df["repo_path"] = repo_url
            return commits_add_delete_and_stars_df
        except Exception as e:
            print(f"Request for {repo_url} failed due to {e}")
            return pd.DataFrame(
                columns=[
                    "starred_at",
                    "stargazer_list",
                    "stargazer_size",
                    "week",
                    "additions",
                    "deletions",
                    "total_commits",
                    "commits_per_day",
                    "repo_path",
                ]
            )


from dataclasses import dataclass
from bs4 import BeautifulSoup
import requests
from rich.progress import track
from rich import print
import pandas as pd
import os
import warnings
from dotenv import load_dotenv
from typing import List
from IPython import get_ipython
from tqdm import tqdm
import logging


load_dotenv()
warnings.filterwarnings("ignore")

TYPES = ["Users", "Repositories", "Code", "Commits", "Issues", "Packages", "Topics"]
SORT_BY = {"Users": ["followers"], "Repositories": ["", "stars"]}
SCRAPE_CLASS = {"Users": "mr-1", "Repositories": "v-align-middle"}


USERNAME = os.getenv("GITHUB_USERNAME_LIVE")
TOKEN = os.getenv("GITHUB_TOKEN_LIVE")

if USERNAME is None or TOKEN is None:
    logging.warning(
        """You are using Github API as an unauthenticated user. For unauthenticated requests, the rate limit allows for up to 60 requests per hour.
     Follow the instruction here to be authenticated and increase your rate limit: https://github.com/khuyentran1401/top-github-scraper#setup"""
    )


class ScrapeGithubUrl:
    """Scrape top Github urls based on a certain keyword and type

    Parameters
    -------
    keyword: str
        keyword to search on Github
    type: str
        whether to search for User or Repositories
    sort_by: str
        sort by best match or most stars, by default 'best_match', which will sort by best match.
        Use 'stars' to sort by most stars.
    start_page_num: int
        page number to start scraping. The default is 0
    stop_page_num: int
        page number to stop scraping

    Returns
    -------
    List[str]
    """

    def __init__(
        self,
        keyword: str,
        type: str,
        sort_by: str,
        start_page_num: int,
        stop_page_num: int,
    ):
        self.keyword = keyword
        self.type = type
        self.start_page_num = start_page_num
        self.stop_page_num = stop_page_num
        if sort_by == "best_match":
            self.sort_by = ""
        else:
            self.sort_by = sort_by

    @staticmethod
    def _keyword_to_url(page_num: int, keyword: str, type: str, sort_by: str):
        """Change keyword to a url"""
        keyword_no_space = ("+").join(keyword.split(" "))
        return f"https://github.com/search?o=desc&p={str(page_num)}&q={keyword_no_space}&s={sort_by}&type={type}"

    def _scrape_top_repo_url_one_page(self, page_num: int):
        """Scrape urls of top Github repositories in 1 page"""
        url = self._keyword_to_url(
            page_num, self.keyword, type=self.type, sort_by=self.sort_by
        )
        page = requests.get(url)

        soup = BeautifulSoup(page.text, "html.parser")
        a_tags = soup.find_all("a", class_=SCRAPE_CLASS[self.type])
        urls = [a_tag.get("href") for a_tag in a_tags]

        return urls

    def scrape_top_repo_url_multiple_pages(self):
        """Scrape urls of top Github repositories in multiple pages"""
        urls = []
        if isnotebook():
            for page_num in tqdm(
                range(self.start_page_num, self.stop_page_num),
                desc="Scraping top GitHub URLs...",
            ):
                urls.extend(self._scrape_top_repo_url_one_page(page_num))
        else:
            for page_num in track(
                range(self.start_page_num, self.stop_page_num),
                description="Scraping top GitHub URLs...",
            ):
                urls.extend(self._scrape_top_repo_url_one_page(page_num))

        return urls


class UserProfileGetter:
    """Get the information from users' homepage"""

    def __init__(self, urls: List[str]) -> pd.DataFrame:
        self.urls = urls
        self.profile_features = [
            "login",
            "url",
            "type",
            "name",
            "company",
            "location",
            "email",
            "hireable",
            "bio",
            "public_repos",
            "public_gists",
            "followers",
            "following",
        ]

    def _get_one_user_profile(self, profile_url: str):
        profile = requests.get(profile_url, auth=(USERNAME, TOKEN)).json()
        return {
            key: val for key, val in profile.items() if key in self.profile_features
        }

    def get_all_user_profiles(self):

        if isnotebook():
            all_contributors = [
                self._get_one_user_profile(url)
                for url in tqdm(self.urls, desc="Scraping top GitHub profiles...")
            ]
        else:
            all_contributors = [
                self._get_one_user_profile(url)
                for url in track(
                    self.urls, description="Scraping top GitHub profiles..."
                )
            ]
        all_contributors_df = pd.DataFrame(all_contributors).reset_index(drop=True)

        return all_contributors_df
