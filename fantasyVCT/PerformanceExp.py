import pandas as pd


class Scraper:
    # TODO: accept match code. Right now from outer scope
    def __init__(self, match_code):
        self.match_code = match_code
        self.url = 'string'
        self.matches = ''
        self.df = ''

    def scrape_url(self):
        print('2')
        self.url = 'https://www.vrl.gg/' + match_code + '/?game=all&tab=' + self.game_type  # Get "link" for scraping
        print('2.5')
        # ERROR IN LINE 17 "<urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>"
        self.matches = pd.read_html(self.url)  # Compilation of all tables in static page
        print("3")

    def clean_data(self):
        print('9')
        self.df.fillna("0 0", inplace=True)  # Replace all NaN values with strings
        self.df.rename(columns={'Unnamed: 0': 'Player'}, inplace=True)          # Name Player column
        self.df[['Player', 'Team']] = df['Player'].str.split(n=1, expand=True)  # Split Player column into Player/Team
        print('10')
        # Dump extraneous information
        for k in range(len(self.cols)):
            self.df[[self.cols[k], 'd' + str(k)]] = self.df[self.cols[k]].str.split(n=1, expand=True)
            print('11')
        # Reorganize table
        self.df = self.df[['Player'] + self.cols]

    def organize_data(self):
        print('8')
        for j in range(self.games):
            self.df = pd.read_html(self.url)[self.tables[j]]  # Parse table
            self.clean_data()
            self.tables[j] = df  # Add dataframe to list
        print('12')


class PerformanceScraper(Scraper):

    def __init__(self):
        super().__init__(match_code)
        self.game_type = 'performance'
        self.cols = ['2K', '3K', '4K', '5K', '1v1', '1v2', '1v3', '1v4', '1v5']  # Statistic titles
        self.games = int(len(self.matches) / 4 - 1)     # Total number of games
        self.tables = list(range(self.games))           # Placeholders for tables

    def which_games(self):
        print('5')
        # Check if there are any games for given match code
        if self.games == 0:
            # TO DO: table filled with zeros
            print("No Matches Up")
        # Make tables list hold table index for each map
        for i in range(games):
            self.tables[i] = 4 * (i + 1) + 3
        print('6')

    def final_tables(self):
        print("1")
        Scraper.scrape_url(self)
        print('4')
        self.which_games()
        print('7')
        Scraper.organize_data(self)


# Will parse through tables and extract/organize information
class ParseTable:
    def __init__(self):
        self.player = ''
        self.team = ''
        self.match = ''


match_code = '41573'
b = Performance_Scraper()
tables = b.final_tables(match_code)
print('termines')
print(tables)
