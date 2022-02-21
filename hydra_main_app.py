from hydralit import HydraApp
import hydralit_components as hc
import apps
import streamlit as st

# Only need to set these here as we are add controls outside of Hydralit, to customise a run Hydralit!
st.set_page_config(
    page_title="",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="auto",
)

if __name__ == "__main__":

    over_theme = {
        "txc_inactive": "#1A1CRF",
        "menu_background": "grey",
        "txc_active": "white",
        # "option_active": "blue",
    }
    # this is the host application, we add children to it and that's it!
    app = HydraApp(
        title="",
        favicon="🔭",
        hide_streamlit_markers=False,
        # add a nice banner, this banner has been defined as 5 sections with spacing defined by the banner_spacing array below.
        use_banner_images=[
            {
                "header": "<h1 style='text-align:left;padding: 0px 0px;color:white;font-size:200%;'>Crytpo Social Explorer App</h1><br>"
            },
            # "./images/cryptomeme.gif",
        ],
        banner_spacing=[60],
        use_navbar=True,
        navbar_sticky=True,
        navbar_animation=False,
        navbar_theme=over_theme,
    )

    data_dict = apps.get_sidebar()

    # Home button will be in the middle of the nav list now
    app.add_app(
        "Home",
        icon="🏠",
        app=apps.MainApp(
            title="Home",
            data=data_dict["data"],
            coin_choice=data_dict["coin_choice"],
            coin_id=data_dict["coin_id"],
        ),
        is_home=True,
    )
    app.add_app(
        "Github Repo Graph",
        icon="🧑‍💻",
        app=apps.GraphApp(
            title="Repo Graph",
            coin_choice=data_dict["coin_choice"],
        ),
        is_home=False,
    )
    app.add_app(
        "Github Live Scraper",
        icon="🔭",
        app=apps.RepoScraperApp(
            title="Repo Scraper App",
            data=data_dict["data"],
            coin_choice=data_dict["coin_choice"],
        ),
        is_home=False,
    )

    # add all your application classes here
    # app.add_app("Cheat Sheet", icon="📚", app=apps.CheatApp(title="Cheat Sheet"))
    # app.add_app("Sequency Denoising",icon="🔊", app=apps.WalshApp(title="Sequency Denoising"))
    # app.add_app("Sequency (Secure)",icon="🔊🔒", app=apps.WalshAppSecure(title="Sequency (Secure)"))
    # app.add_app("Solar Mach", icon="🛰️", app=apps.SolarMach(title="Solar Mach"))
    # app.add_app("Spacy NLP", icon="⌨️", app=apps.SpacyNLP(title="Spacy NLP"))
    # app.add_app("Uber Pickups", icon="🚖", app=apps.UberNYC(title="Uber Pickups"))
    # app.add_app("Solar Mach", icon="🛰️", app=apps.SolarMach(title="Solar Mach"))
    # app.add_app("Loader Playground", icon="⏲️", app=apps.LoaderTestApp(title="Loader Playground"))
    # app.add_app("Cookie Cutter", icon="🍪", app=apps.CookieCutterApp(title="Cookie Cutter"))

    # #we have added a sign-up app to demonstrate the ability to run an unsecure app
    # #only 1 unsecure app is allowed
    # app.add_app("Signup", icon="🛰️", app=apps.SignUpApp(title='Signup'), is_unsecure=True)

    # we want to have secure access for this HydraApp, so we provide a login application
    # optional logout label, can be blank for something nicer!
    # app.add_app("Login", apps.LoginApp(title='Login'),is_login=True)

    # specify a custom loading app for a custom transition between apps, this includes a nice custom spinner
    app.add_loader_app(apps.MyLoadingApp(delay=0))

    # complex_nav = {
    #     "Home": ["Home"],
    #     # "Loader Playground": ["Loader Playground"],
    #     # "Intro 🏆": ["Cheat Sheet", "Solar Mach"],
    #     # "Hotstepper 🔥": ["Sequency Denoising"],
    #     # "Clustering": ["Uber Pickups"],
    #     # "NLP": ["Spacy NLP"],
    #     # "Cookie Cutter": ["Cookie Cutter"],
    # }

    # and finally just the entire app and all the children.
    app.run()
