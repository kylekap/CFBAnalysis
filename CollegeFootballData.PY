import time
import numpy as np
import pandas as pd
import requests

start = time.time()
print('*'*100)

#Setting Variables
filename = r'[Filepath_Here]' #saving here
url = 'https://api.collegefootballdata.com' #URL for pulls
years = range(2019,2020) #years of data to pull. iterated over below
dropcols = ['away_post_win_prob', 'home_post_win_prob', 'away_line_scores', 'home_line_scores','attendance'] #Columns to remove. Contain data not analyzed in this code

def getgames(ayear):
    #Gets all games for a given year in dataframe form.
    passedparameters = dict(year=ayear)
    r = requests.get(url+'/games',params=passedparameters)
    df = pd.DataFrame(r.json())
    #remove the unused columns here, before passing back to main function
    df.drop(dropcols,inplace=True, axis=1)
    return df

def getteamstats(ayear,week):
    passedparameters = dict(year=ayear,week=week)
    r = requests.get(url+'/games/teams',params=passedparameters)
    df = pd.io.json.json_normalize(r.json(),['teams','stats'], ['id',['teams','school'],['teams','conference'],['teams','homeAway'],['teams','points']], sep="_", errors='ignore')
    df = df.pivot_table(values='stat',index=['id','teams_school'],columns=['category'], aggfunc='first').reset_index()
    return df

def redefine_non_fbs(dfin):
    #Anything Non-FBS (aka no conference) gets redefined to be the same team to alleviate one-off games by these teams in the data
    dfout = dfin
    dfout['away_conference'].fillna(value="Non-FBS",inplace=True)
    dfout['home_conference'].fillna(value="Non-FBS",inplace=True)
    dfout.loc[dfout.away_conference=='Non-FBS', 'away_team'] = 'Non-FBS'
    #dfout = dfout[dfout.home_conference != 'Non-FBS']
    #dfout = dfout[dfout.away_conference != 'Non-FBS']
    return dfout

def reframe_data(df):
    df1 = df
    df1.rename(columns ={'away_conference':'team_conference','away_points':'team_points','away_team':'team','home_conference':'opp_conference','home_points':'opp_points','home_team':'opp'}, inplace=True)
    df2 = df1.rename(columns={'team_conference':'opp_conference','team_points':'opp_points','team':'opp','opp_conference':'team_conference','opp_points':'team_points','opp':'team'}, inplace=False)
    df2['home_or_away'] = 'home'
    df1['home_or_away'] = 'away'
    df1 = df1.append(df2,sort=True)
    df1['point_diff'] = df1['team_points']-df1['opp_points']
    #df1['point_diff'].values[df1['point_diff'] > 24] = 24
    #df1['point_diff'].values[df1['point_diff'] < -24] = -24
    return df1

def create_avg_dataframe(df,colmean,colname):
    dfgrouped = df.groupby('team').agg({colmean:'mean'}).reset_index()
    dfgrouped.set_index('team')
    dfgrouped.rename(columns={colmean:colname},inplace=True)
    return dfgrouped

def get_game_data(years):
    for theyear in years: 
        #for each year, import the data
        if theyear == min(years):
            #first year, build the dataframes
            dfgames = getgames(theyear)
        else:
            #subsequent years, append dataframe with new data
            dfgames = dfgames.append(getgames(theyear),sort=False)
    return dfgames

def get_stat_data(years):
    for theyear in years: 
        #for each year, import the data
        if theyear == min(years):
            for week in range(1,16):
                if week == 1:
                    dfstats = getteamstats(theyear,week)
                else:
                    dfstats = dfstats.append(getteamstats(theyear,week), sort=False)
        else:
            #subsequent years, append dataframe with new data
            for week in range(1,16):
                dfstats = dfstats.append(getteamstats(theyear,week), sort=False)
    return dfstats

def clean_stats(df):
    #Missing Stats = 0's
    df.fillna(0,inplace=True) 

    #Make Completions & Pass Attemps separate columns. Calculates Completion % as well
    temp = df['completionAttempts'].str.split('-', n=1,expand=True)
    df['completionSuccess'] = temp[0]
    df['completionAttempts'] = temp[1]
    df['completionPercentage'] = pd.to_numeric(df['completionSuccess'], errors='coerce')/pd.to_numeric(df['completionAttempts'], errors='coerce')

    #Make penalties and penalty yardage separate
    temp = df['totalPenaltiesYards'].str.split('-', n=1,expand=True)
    df['totalPenalties'] = temp[0]
    df['totalPenaltiesYards'] = temp[1]

    #Make Third down successes and third down attempts separate. Calculate third down % efficiency
    temp = df['thirdDownEff'].str.split('-', n=1,expand=True)
    df['thirdDownSuccess'] = temp[0]
    df['thirdDownAttempts'] = temp[1]
    df['thirdDownEff'] = pd.to_numeric(df['thirdDownSuccess'], errors='coerce')/pd.to_numeric(df['thirdDownAttempts'], errors='coerce')
 
    #Make Fourth down successes and fourth down attempts separate. Calculate fourth down % efficiency
    temp = df['fourthDownEff'].str.split('-', n=1,expand=True)
    df['fourthDownSuccess'] = temp[0]
    df['fourthDownAttempts'] = temp[1]
    df['fourthDownEff'] = pd.to_numeric(df['fourthDownSuccess'], errors='coerce')/pd.to_numeric(df['fourthDownAttempts'], errors='coerce')
    
    return df


dfgames = get_game_data(years) #Get overall data for each game
dfstats = get_stat_data(years) #Get statistical data for each game

dfgames = redefine_non_fbs(dfgames) #change all non-FBS information
dfgames = reframe_data(dfgames)

dfstats = clean_stats(dfstats) #Redefining values to better fit into display methods.

dfcombine = dfgames.merge(dfstats, how='left', left_on=['id','team'], right_on=['id','teams_school'])

dfstats.to_csv(filename+'_stats.csv',index = None, header=True)
dfgames.to_csv(filename+'_games.csv', index=None, header=True)
dfcombine.to_csv(filename+'_combined.csv', index=None, header=True)

print('*'*100)
print('time taken:',time.time()-start)
