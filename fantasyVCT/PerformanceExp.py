import pandas as pd

class Scraper():

    def scrape_url(self, match_code, game_type):
        print('2')
        url = 'https://www.vrl.gg/' + match_code + '/?game=all&tab=' + game_type  # Get "link" for scraping
        print('2.5')
        # ERROR IN LINE 10 "<urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>"
        matches = pd.read_html(url)  # Compilation of all tables in static page
        print("3")
        return url, matches

    def clean_data(self, df, cols):
        print('9')
        df.fillna("0 0", inplace=True)  # Replace all NaN values with strings
        df.rename(columns={'Unnamed: 0': 'Player'}, inplace=True)  # Name Player column
        df[['Player', 'Team']] = df['Player'].str.split(n=1, expand=True)  # Split Player column into Player and Team
        print('10')
        for k in range(len(cols)):
            df[[cols[k], 'd' + str(k)]] = df[cols[k]].str.split(n=1, expand=True)  # Dump extraneous information
            print('11')
        return df[['Player'] + cols]

    def organize_data(self, url, games, tables, cols):
        print('8')
        for j in range(games):
            df = pd.read_html(url)[tables[j]]  # Parse table
            self.clean_data(df, cols)
            tables[j] = df  # Add dataframe to list
        print('12')
        return tables


class Performance_Scraper(Scraper):

    def which_games(self, matches):
        print('5')
        cols = ['2K', '3K', '4K', '5K', '1v1', '1v2', '1v3', '1v4', '1v5']  # Statistic titles
        games = int(len(matches) / 4 - 1)  # Total number of games
        tables = list(range(games))  # Placeholders for tables
        # Check if there are any games for given match code
        if games == 0:
            # TO DO: table filled with zeros
            print("No Matches Up")
        # Make tables list hold table index for each map
        for i in range(games):
            tables[i] = 4 * (i + 1) + 3
        print('6')
        return cols, games, tables

    def final_tables(self, match_code):
        game_type = 'performance'
        print("1")
        url, matches = Scraper.scrape_url(self, match_code, game_type)
        print('4')
        cols, games, tables = self.which_games(matches)
        print('7')
        return Scraper.organize_data(url, games, tables, cols)


match_code = '41573'
b = Performance_Scraper()
tables = b.final_tables(match_code)
print('termines')
print(tables)