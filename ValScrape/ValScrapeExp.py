import pandas as pd

# link = input("URL? \n")   # Set vrl.gg performance URL as variable "link"
# url = r link              # Read in link
url = r'https://www.vlr.gg/25193/version1-vs-100-thieves-champions-tour-north-america-stage-3-challengers-1-ubqf/?game=all&tab=performance'

match = pd.read_html(url)   # Total number of tables in static page
games = len(ball)/4-1       # Total number of games
tables =[7, 11, 15]         # Tables of games 1, 2, and/or 3

#
if games == 2:
    tables = tables[0:2]
elif games == 1:
    tables = tables[0]
elif games == 0:
    # table filled with zeros
    tables = tables

for i in tables:
    print(i)
    # creates a different dataframe, to put all the data frames into a tuple
    df = pd.read_html(url)[i]
    df.fillna("0 d", inplace=True)
    df.rename(columns={'Unnamed: 0':'Player'}, inplace=True)
    df[['Player', 'Team']] = df['Player'].str.split(n=0, expand=True)
    df[['2K', 'd0']] = df['2K'].str.split(n=1, expand=True)
    df[['3K', 'd1']] = df['3K'].str.split(n=1, expand=True)
    df[['4K', 'd2']] = df['4K'].str.split(n=1, expand=True)
    df[['5K', 'd3']] = df['5K'].str.split(n=1, expand=True)
    df[['1v1', 'd4']] = df['1v1'].str.split(n=1, expand=True)
    df[['1v2', 'd5']] = df['1v2'].str.split(n=1, expand=True)
    df[['1v3', 'd6']] = df['1v3'].str.split(n=1, expand=True)
    df[['1v4', 'd7']] = df['1v4'].str.split(n=1, expand=True)
    df[['1v5', 'd8']] = df['1v5'].str.split(n=1, expand=True)
    df = df[['Player', '2K', '3K', '4K', '5K', '1v1', '1v2', '1v3', '1v4', '1v5']]