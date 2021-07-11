import pandas as pd

# TO DO: Create "performance scraper" class -- subclass to "scraper" class
# TO DO: Figure out how to read in modular URL
# link = 'vrl.gg/' + input("Match code? \n") + '/?game=all&tab=performance' # Get "link" for scraping
# url = r link  # Read in link
url = r'https://www.vlr.gg/25193/?game=41573&tab=performance'    # placeholder

match = pd.read_html(url)               # Total number of tables in static page
games = int(len(match)/4-1)             # Total number of games
tables = list(range(games))             # Placeholders for tables
# Check if there are any games for given match code
if games == 0:
    # TO DO: table filled with zeros
    print("No Matches Up")
# Make tables list hold table index for each map
for i in range(games):
    tables[i] = 4 * (i+1) + 3

cols = ['2K', '3K', '4K', '5K', '1v1', '1v2', '1v3', '1v4', '1v5']  # Statistic titles
# Parse, clean, and organize dataframes
for j in range(games):
    df = pd.read_html(url)[tables[j]]                                   # Parse table
    df.fillna("0 0", inplace=True)                                      # Replace all NaN values with strings
    df.rename(columns={'Unnamed: 0':'Player'}, inplace=True)            # Name Player column
    df[['Player', 'Team']] = df['Player'].str.split(n=1, expand=True)   # Split Player column into Player and Team
    for k in range(len(cols)):
        df[[cols[k], 'd'+str(k)]] = df[cols[k]].str.split(n=1, expand=True)     # Dump extraneous information
    df = df[['Player'] + cols]                                                  # Re-organize dataframe
    tables[j] = df                                                              # Add dataframe to list