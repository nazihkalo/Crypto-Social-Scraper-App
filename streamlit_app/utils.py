import base64

import pandas as pd
import streamlit as st
from streamlit.uploaded_file_manager import UploadedFile
import streamlit.components.v1 as components
import json
from datetime import datetime

from .repo import get_all_commits


DATE_COLUMN = 'last_updated'
coin_file_path = "./streamlit_app/coin_info/coin_socials.json"


### COINGECKO
@st.cache
def load_coingecko_data():
    try:
        with open(coin_file_path, "r") as file:
            jj = json.load(file)
        coin_social_data_df = pd.DataFrame.from_dict(jj,orient = "index")
        print(f"Read df with {coin_social_data_df.shape} rows ")
        # lowercase = lambda x: str(x).lower()
        # data.rename(lowercase, axis='columns', inplace=True)
        coin_social_data_df[DATE_COLUMN] = pd.to_datetime(coin_social_data_df[DATE_COLUMN])
        # Create a text element and let the reader know the data is loading.
        return coin_social_data_df
    except Exception as e:
        # Notify the reader that the data was successfully loaded.
        st.sidebar.error('Error loading data :(') 
        return None   

def get_description(data, coin_choice):
    description_text = data.loc[data.name == str(coin_choice), 'description'][0].get("en","")
    return description_text


####GITHUB
@st.cache
def get_repo_data(repo_path, since = None, to = None, first_n_commits = None):
    """
    Retrieve commit history from remote source or local .json file
    Args:
        repo_path: File st.text_input or st.file_uploader
    Returns:
        pandas.DataFrame: A dataframae containing the commit history
    """
    if isinstance(repo_path, UploadedFile):
        data = pd.read_json(repo_path, orient="records")
    else:
        commits = get_all_commits(repo_path, since = since, to = to, first_n_commits = first_n_commits)
        if len(commits) == 0:
            data = pd.DataFrame({"hash":pd.Series(['NA'], dtype='str'),
            "author":pd.Series(['NA'],dtype='str'),
            "committed_on":pd.date_range(datetime.now().date(), periods=1, freq='D'),
            "authored_on":pd.date_range(datetime.now().date(), periods=1, freq='D'),
            "lines_added":pd.Series([0],dtype='int'),
            "lines_deleted":pd.Series([0],dtype='int'),
            "files_touched":pd.Series([0],dtype='int'),
            "is_merge":pd.Series([0],dtype='int'),
            "message":pd.Series(['NA'],dtype='str')})

        else:
            data = pd.DataFrame(commits)
            

    # Convert timestamps
    data[["committed_on", "authored_on"]] = data[["committed_on", "authored_on"]].apply(
        pd.to_datetime
    )
    data['total_lines'] = data['lines_added'] + data['lines_deleted']

    return data



def get_top_contributors(data):
    """Rank contributors by number of commits"""
    # fmt: off
    res = (
        data.groupby("author")["hash"]
            .count()
            .sort_values(ascending=False)
            .reset_index()
    )
    res.columns = ["author", "n_commits"]
    return res


def get_repo_stats(data):
    """Get some high level repository statistics"""
    repo_stats = {
        "Commits": (f"{data['hash'].count():,}", "📃"),
        "Merges": (f"{data['is_merge'].value_counts()[0]:,}", "🔃"),
        "Contributors": (f"{data['author'].nunique():,}", "👨‍💻"),
        "Lines Added": (f"{data['lines_added'].sum():,}", "➕"),
        "Lines Deleted": (f"{data['lines_deleted'].sum():,}", "➖")
    }

    return repo_stats


def get_contributor_stats(data, contributor):
    """
    Gets some high level statistics on a given contributor
    Args:
        data (pd.DataFrame): A commit history
        contributor (str): The name of the target contributor
    Returns:
        (tuple): tuple containing:
            stats (dict): Dict containing contributor metrics
            quarterly_contrib (pd.DataFrame): Dataframe with n. contributions by quarter.
    """
    if not contributor:
        return None, None

    activity = data[data['author'] == contributor]
    n_commits = len(activity)

    # Lines of code stats
    tot_lines = activity['lines_added'].sum() + activity['lines_deleted'].sum()
    pct_change = n_commits / len(data)
    tot_l_added = activity['lines_added'].sum()
    tot_l_deleted = activity['lines_deleted'].sum()
    pct_l_deleted = tot_l_deleted / tot_lines
    pct_l_added = tot_l_added / tot_lines
    avg_change = activity['total_lines'].mean()

    # Total changes by quarter
    quarterly_contrib = (
        activity.groupby(pd.Grouper(key='committed_on', freq="1Q"))['hash']
            .count()  # noqa: E131
            .reset_index()
    )
    return {
        "Commits": (f"{n_commits}", "📜"),
        "Total Lines": (f"{tot_lines:,}", "🖋️"),
        "Lines Added": (f"{tot_l_added:,}", "🖋️"),
        "% Lines Added": (f"{pct_l_added * 100:,.3}", "✅"),
        "Lines Deleted": (f"{tot_l_deleted:,}", "❌"),
        "% Lines Deleted": (f"{pct_l_deleted * 100:,.3}", "❌"),
        "% of Total Changes": (f"{pct_change * 100:,.3}", "♻️"),
        "Avg. Change (lines)": (f"{avg_change:,.2f}", "♻️"),
        "Contributor": (contributor, "👨‍💻")
    }, quarterly_contrib


def filter_by_date(df, start, end):
    """Filter dataframe by date"""
    df = df[(df['committed_on'] >= str(start)) & (df['committed_on'] <= str(end))]
    return df


def filter_by_contributor(df, x):
    """Filter dataframe by contributor"""
    if not x:
        return df
    else:
        df = df[df['author'] == x]
        return df


def download_data(data):
    """
    Download data in .csv format
    Args:
        data (`pd.DataFrame`): A pandas dataframe
    Returns:
        str: A href link to be fed into the dashboard ui.
    """
    to_download = data.to_csv(index=False)
    b64 = base64.b64encode(to_download.encode()).decode()
    href = f'<a href="data:file/text;base64,{b64}">Download csv file</a>'

    return href


from google.oauth2 import service_account
from google.cloud import bigquery

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)

# Perform query.
# Uses st.cache to only rerun when the query changes or after 10 min.
@st.experimental_memo 
def run_query(query):
    query_job = client.query(query)
    # rows_raw = query_job.result()
    result_df = query_job.result().to_dataframe()
    # Convert to list of dicts. Required for st.cache to hash the return value.
    # rows = [dict(row) for row in rows_raw]
    return result_df




def get_coin_multiple_repos_stats(repo_paths):
    if len(repo_paths) > 0:
        query = f''' SELECT * FROM `steady-voltage-236500.github_repo_commits.github_repo_stats_historyv2` where repo_path in ({",".join(repo_paths)})'''
        results_df = run_query(query)
        return results_df
    return pd.DataFrame()


###### GRAPH UTILS

from operator import itemgetter

def knn(graph, node, n):
    return [e[1] for e in sorted(graph.edges(node,data=True),key= lambda x: x[2]['weight'],reverse=True)[:n]]
    # return list(map(itemgetter(1),
    #                 sorted([(e[2]['weight'], e[1])
    #                         for e in graph.edges(node, data=True)])[:n]))
# knn(MG,  "Fantom", 5)

@st.experimental_memo
def load_netowrkxgraph():
    import networkx as nx
    MG = nx.read_gpickle('streamlit_app/coin_info/graph_contributor_edges.pkl')
    return MG

# Build subgraph containing a subset of the nodes, and edges between those nodes
def get_subgraph(G, top_n_nodes = None, nearest_nodes = None, n = 20):
    if top_n_nodes:
        nodes = [index for index, values in  sorted(G.nodes(data=True),key= lambda x: x[1]['stargazers_count'],reverse=True)[:top_n_nodes]]
        subgraph = G.subgraph(nodes)
    if nearest_nodes:
        nodes = knn(G,  nearest_nodes, n)
        nodes.extend([nearest_nodes])
        subgraph = G.subgraph(nodes)
    
    return subgraph

options = '''var options = {
    "height": "1000",
  "width": "1000",
  "configure": {
        "enabled": false,
        "showButton": false
   },
    "nodes":{
        "showButton": false
    },
  "edges": {
    "color": {
      "color": "rgba(0,163,255,0.63)",
      "highlight": "rgba(209,0,9,1)",
      "hover": "rgba(132,0,96,1)",
      "inherit": false,
      "opacity": 0.3
    },
    "dashes": true,
    "font": {
      "size": 10
    },
    "scaling": {
      "min": 0,
      "max": 6,
      "label": {
        "min": 0,
        "max": 5,
        "maxVisible": 15,
        "drawThreshold": 2
      }
    },
    "shadow": {
      "enabled": true
    },
    "interaction": {
    "hover": true},
    "smooth": false
  },
  "interaction": {
    "hover": true,
    "multiselect": false,
    "navigationButtons": false,
    "showButton": false
    
  },
  "physics": {
    "hierarchicalRepulsion": {
      "centralGravity": 0,
      "springLength": 400
    },
    "minVelocity": 0.75,
    "solver": "hierarchicalRepulsion"
  }
}'''

from pyvis.network import Network
import networkx as nx
from pyvis import network as net

def draw_graph3(networkx_graph,notebook=True,output_filename='graph.html',show_buttons=False,only_physics_buttons=False,
                height=None,width=None,bgcolor=None,font_color=None, color_node = None, pyvis_options=None):
    """
    This function accepts a networkx graph object,
    converts it to a pyvis network object preserving its node and edge attributes,
    and both returns and saves a dynamic network visualization.
    Valid node attributes include:
        "size", "value", "title", "x", "y", "label", "color".
        (For more info: https://pyvis.readthedocs.io/en/latest/documentation.html#pyvis.network.Network.add_node)
    Valid edge attributes include:
        "arrowStrikethrough", "hidden", "physics", "title", "value", "width"
        (For more info: https://pyvis.readthedocs.io/en/latest/documentation.html#pyvis.network.Network.add_edge)
    Args:
        networkx_graph: The graph to convert and display
        notebook: Display in Jupyter?
        output_filename: Where to save the converted network
        show_buttons: Show buttons in saved version of network?
        only_physics_buttons: Show only buttons controlling physics of network?
        height: height in px or %, e.g, "750px" or "100%
        width: width in px or %, e.g, "750px" or "100%
        bgcolor: background color, e.g., "black" or "#222222"
        font_color: font color,  e.g., "black" or "#222222"
        pyvis_options: provide pyvis-specific options (https://pyvis.readthedocs.io/en/latest/documentation.html#pyvis.options.Options.set)
    """

    # import
    from pyvis import network as net
    import numpy as np

    # make a pyvis network
    network_class_parameters = {"notebook": notebook, "height": height, "width": width, "bgcolor": bgcolor, "font_color": font_color}
    pyvis_graph = net.Network(**{parameter_name: parameter_value for parameter_name, parameter_value in network_class_parameters.items() if parameter_value})
    pyvis_graph.hrepulsion(central_gravity=0, spring_length = 400)
    # for each node and its attributes in the networkx graph
    max_stars = max([node_attrs['stargazers_count'] for node,node_attrs in networkx_graph.nodes(data=True)])
    for node,node_attrs in networkx_graph.nodes(data=True):
        node_size = np.log10(int(node_attrs['stargazers_count']))*3
        # node_size = node_attrs['stargazers_count'] / max_stars
        # pyvis_graph.add_node(node,size = node_size,**node_attrs)
        hover_text = f"<h1>{node}</h1>"
        hover_text += f" <strong>Stargazers:{node_attrs['stargazers_count']:,.0f}<strong><br>"
        hover_text += f" <strong>Forks:{node_attrs['forks_count']:,.0f}</strong><br>"
        hover_text += ' <h2>Repos:</h2><br>' + '<br>'.join([f'<font size="1">{repo}</font>' for repo in node_attrs["repos"]])
        if node == color_node:
            pyvis_graph.add_node(node, label = node, title = hover_text, size = node_size, color = 'red', opacity = 0.3)
        else:    
            pyvis_graph.add_node(node, label = node, title = hover_text, size = node_size)
    max_edge_weigth = max([x[2]['weight'] for x in networkx_graph.edges(data=True)])
    # for each edge and its attributes in the networkx graph
    for source,target,edge_attrs in networkx_graph.edges(data=True):
        # if value/width not specified directly, and weight is specified, set 'value' to 'weight'
        if not 'value' in edge_attrs and not 'width' in edge_attrs and 'weight' in edge_attrs:
            # place at key 'value' the weight of the edge
            edge_attrs['width'] = edge_attrs['weight'] / (max_edge_weigth*2)
            edge_attrs['title'] = f"<strong>{source} & {target} share {edge_attrs['weight']} git contributors</strong>" 
            edge_attrs['value'] = f"{source} & {target} share {edge_attrs['weight']} git contributors" 
            edge_attrs['label'] = f"Shared Contributors={edge_attrs['weight']}"
        # add the edge
        pyvis_graph.add_edge(source,target,**edge_attrs)
    
    neighbor_map = pyvis_graph.get_adj_list()
    # max_edges = max([len(i) for i in neighbor_map.values()])
    # max_edges = max([len(i) for i in neighbor_map.values()])
    for node in pyvis_graph.nodes:
        # node['value'] = len(neighbor_map[node['id']])/ max_edges
        node['title'] +=  f' <strong>Neighboring Tokens: {len(neighbor_map[node["id"]]) }</strong><br>'
        

    # pyvis-specific options
    if pyvis_options:
        pyvis_graph.set_options(pyvis_options)

    # turn buttons on
    # if show_buttons:
    #     if only_physics_buttons:
    #         pyvis_graph.show_buttons(filter_=['physics'])
    #     else:
    #         pyvis_graph.show_buttons()

    

    # return and also save
    # return pyvis_graph.show(output_filename)
    return pyvis_graph.write_html(output_filename)


def get_subgraph_info(coin_choice, n):
    MG = load_netowrkxgraph()
    subgraph = get_subgraph(MG, nearest_nodes = coin_choice, n = n)
    
    # Save and read graph as HTML file (on Streamlit Sharing)
    try:
        path = '/tmp'
        graph = draw_graph3(subgraph, output_filename= f'{path}/pyvis_graph.html', color_node = coin_choice,width = 1000, height = 1000, show_buttons=False,only_physics_buttons=True, pyvis_options=options)
        HtmlFile = open(f'{path}/pyvis_graph.html', 'r', encoding='utf-8')

    # Save and read graph as HTML file (locally)
    except:
        path = '/html_files'
        graph = draw_graph3(subgraph, output_filename= f'{path}/pyvis_graph.html',color_node = str(coin_choice), show_buttons=False,only_physics_buttons=True,  pyvis_options=options)
        HtmlFile = open(f'{path}/pyvis_graph.html', 'r', encoding='utf-8')

    # Load HTML file in HTML component for display on Streamlit page
    st.markdown(f"Showing {n} Nearest Nodes to {coin_choice} based on overlapping contributor counts")
    with open("streamlit_app/components/style.css") as f:
        # col1, col2, col3 = st.columns([400,1000,1])
        # with col2:
        st.markdown('<style>{}</style>'.format(f.read()), unsafe_allow_html=True)
        components.html(HtmlFile.read(), width= 1000, height=1000)
    
    
