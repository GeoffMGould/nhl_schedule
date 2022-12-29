## 2 of 3 in NHL package. Takes list of games generated in Part 1 and generates
## full schedule for 2022-2023 season.

import pandas as pd; import numpy as np; import re; import random; import sys
from haversine import haversine, Unit; import math
from nhl_make_games_list import nhl_info
from nhl_make_games_list import games_played_list
from nhl_make_games_list import teams_list

#Set working directory
#import os; #os.chdir("/Users/Geoff/Documents/Python")

###*** PART 1 ***####
#SETUP

#initialize constants
start_ind = 0; end_ind = 6; opening_day = "2022-10-11"; season_weeks = 30
super_bowl = "2023-02-12"; third_xmas_day = ""; current_date = "2022-10-11"

# initialize lists, dicts, df's
games_by_date = {} # each key is a day in "YYYY-MM-DD" form. Value is a LIST of all games on that day in AWY-HME form
truth_list = []; all_intervals_list = []; # used in checking if teams are available to play within day of scheduling
season_games_list = [] # new games are added here after being scheduled
daily_list = [] # copy of games_played_list made at the beginning of each day of scheduling
priority_list = [] # at beginning of each day, this list is combed first for games to add (before daily_list)
tomorrow_priority_list = [] # some games from priority_list may be added here. Like other games of away team vs. cluster home teams
today_list = [] # when a game is added, both teams added to this list. Allows teams who don't get scheduled on a day to have their rest day total incremented
season_dates = pd.date_range(pd.to_datetime(opening_day), (pd.to_datetime(opening_day) + pd.to_timedelta(season_weeks,"W")))
cant_host_df = pd.DataFrame(0, index = nhl_info.index, columns = season_dates)
clusters = {
"NW":["EDM","CAL","VAN","SEA"],
"SE":["TBL","FLA","CAR"],
"CALI":["SJS","LAK","ANA"],
"SW":["COL","ARI","VGK"],
"SOUTH": ["DAL","NSH","STL"],
"NYC":["NJD","NYI","NYR"]
}
clusters_list = [team for cluster in clusters.values() for team in cluster]

pac_plus = list(nhl_info[nhl_info["Div"] == "PAC"].index) + ["ARI"]
central_west = ["WIN","MIN","COL"] # removed Dallas in this version
pac_minus = list(set(pac_plus) - set(["EDM","CAL"])) + ["TBL","FLA"] # added FL teams later - keeping name despite geographic inaccuracy because it appears in multiple forms
east_plus = list(nhl_info[nhl_info["Conf"] == "E"].index) + ["CHI"]
north_central = ["WIN","MIN"] # wanted to add chi but makes more sense in east plus, seems less restrictive
north_east = ["MON","OTT","BOS"] # to make cluster for DAL. Will allow getting rid of most usages of long_road_trip which caused conflicts

# determine third day of xmas break which depends on day of week of 12/26
if pd.to_datetime("2022-12-26").strftime("%A") == "Saturday":
    third_xmas_day = "2022-12-23"
else: third_xmas_day = "2022-12-26"

# set Thanksgiving day for reuse in later years to avoid hard-coding
nov_days = pd.date_range("2022-11-01","2022-11-30")
thanksgiving = nov_days[nov_days.strftime("%A") == "Thursday"][3].strftime("%Y-%m-%d")
holidays = ["2022-12-24","2022-12-25",third_xmas_day,thanksgiving,"2023-02-02", "2023-02-03","2023-02-04","2023-02-05"]

## set range and weights which will determine max # of games for each day
## this will make it so more games are scheduled on preferred days (Tu, Th, Sa)
# and fewer on Mon, Wed, Fri
## weights are based on 2022-2023 schedule

## Before Super Bowl - need to adjust these to add more weight to higher numbers. Depends
## on how easily max is reached...
games_by_day_presb = {
"Monday": {"nums": range(3,13), "weights": [.15,.3,.3,.175]+[.0125]*6},
"Tuesday": {"nums": range(6,14), "weights": [.05] * 3 + [.05,.05,.2,.25,.3]},
"Wednesday": {"nums": range(2,8), "weights": [.15,.15,.15,.3,.25,.2]},
"Thursday": {"nums": range(5,15), "weights": [.0125] * 5 + [.15,.15,.25,.2125,.175]},
"Friday": {"nums": range(2,11), "weights": [.1,.28,.27,.1,.08,.08,.04,.04,.01]},
"Saturday": {"nums": range(11,17), "weights": [.05,.05,.15,.25,.25,.25]},
"Sunday": {"nums": range(3,7), "weights": [.2,.25,.25,.3] }
}

## After Super Bowl. More games allowed on Sundays - see above
games_by_day_postsb = {
"Monday": {"nums": range(3,13), "weights": [.15,.3,.3,.175]+[.0125]*6},
"Tuesday": {"nums": range(6,14), "weights": [.05] * 3 + [.1,.1,.2,.25,.2]},
"Wednesday": {"nums": range(2,8), "weights": [.2,.25,.25,.25,.15,.1]},
"Thursday": {"nums": range(5,15), "weights": [.0125] * 5 + [.2,.2,.2,.2125,.125]},
"Friday": {"nums": range(2,11), "weights": [.1,.28,.27,.1,.08,.08,.04,.04,.01]},
"Saturday": {"nums": range(11,17), "weights": [.05,.05,.2,.25,.25,.2]},
"Sunday": {"nums": range(5,10), "weights": [.1,.15] + [.25] * 3 }
}

# df for running totals incremented as time advances
nhl_dynamic = pd.DataFrame(0, index = nhl_info.index, \
columns = ["homestand", "road_trip", "location", "long_road_trip", "away_games","home_games", "games_played","rest_days","rt_first"])
for team in nhl_dynamic.index: # everybody starts at home
    nhl_dynamic.loc[team,"location"] = team
    nhl_dynamic.loc[team,"rt_first"] = team

# this simulates arenas being unavailable b/c of other events. Once or twice a week -
# IRL may or may not vary by size of media market, presence of basketball teams, etc.
# creates df with 1 or 0. 1 signifies arena is not available
for i in range(len(cant_host_df)):
    while end_ind < cant_host_df.shape[1]:
        week_slice = cant_host_df.iloc[i,start_ind:end_ind]
        if random.random() < .50: g = week_slice.sample(2)
        else: g = week_slice.sample(1)
        for j in range(len(g.index)):
           cant_host_df.iloc[i,cant_host_df.columns.get_loc(g.index[j].strftime("%Y-%m-%d"))] = 1
        start_ind += 7; end_ind +=7
    start_ind = 0; end_ind = 6

# Christmas, Thanksgiving, All-Star Break
for holiday in holidays:
    cant_host_df.loc[:,holiday] = 1

### ***** PART 2 ***** ####
## DEFINITIONS OF FUNCTIONS ###
def determine_max_games(dict,day):
    """ THIS FUNCTION DETERMINES THE MAXIMUM NUMBER OF GAMES THAT WILL BE SCHEDULED
    FOR EACH DAY"""
    return random.choices(dict[day]["nums"],dict[day]["weights"])[0]

# 2A Geographical functions
def get_coords(team):
    """ RETURNS COORDINATES IN FORM (LAT,LONG) FOR A TEAM. TAKES 3-LETTER
    TEAM ABBREVIATION AS ARGUMENT """
    latitude = nhl_info.loc[team,"lat"]
    longitude = nhl_info.loc[team,"lng"]
    coords = (latitude,longitude)
    return coords

def measure_distance(team1,team2):
    """ RETURNS DISTANCE BETWEEN TWO TEAMS. TAKES 2 3-LETTER ABBREVIATIONS
    IN TUPLE AS INPUT """
    distance = int(haversine(get_coords(team1),get_coords(team2),unit="mi"))
    return distance

def measure_angle(team1,team2):
    """ MEASURES ANGLE BETWEEN TWO TEAMS, BETWEEN 0-360 CIRCULAR DEGREES """
    tri_point = (nhl_geo.loc[team1,"lat"],nhl_geo.loc[team2,"lng"])
    adjacent = haversine(get_coords(team1),tri_point)
    opposite = haversine(get_coords(team2),tri_point)
    angle = math.degrees(math.atan(opposite/adjacent))
    if (nhl_geo.loc[team2,"lat"] > nhl_geo.loc[team1,"lat"]) & (nhl_geo.loc[team2,"lng"] > nhl_geo.loc[team1,"lng"]): return 90 - angle
    elif (nhl_geo.loc[team2,"lat"] < nhl_geo.loc[team1,"lat"]) & (nhl_geo.loc[team2,"lng"] > nhl_geo.loc[team1,"lng"]): return 90 + angle
    elif (nhl_geo.loc[team2,"lat"] < nhl_geo.loc[team1,"lat"]) & (nhl_geo.loc[team2,"lng"] < nhl_geo.loc[team1,"lng"]): return -(90 + angle)
    elif (nhl_geo.loc[team2,"lat"] > nhl_geo.loc[team1,"lat"]) & (nhl_geo.loc[team2,"lng"] < nhl_geo.loc[team1,"lng"]): return -(90 - angle)

def angle3pt(team1, team2, team3):
     """Counterclockwise angle in degrees by turning from a to c around b
     Returns a float between 0.0 and 360.0"""
     ang = math.degrees(math.atan2(nhl_info.loc[team3,"lat"]-nhl_info.loc[team2,"lat"], nhl_info.loc[team3,"lng"]-nhl_info.loc[team2,"lng"]) \
      - math.atan2(nhl_info.loc[team1,"lat"]-nhl_info.loc[team2,"lat"], nhl_info.loc[team1,"lng"]-nhl_info.loc[team2,"lng"]))
     if -180 < ang < 0:
         return abs(ang)
     elif (ang > 180) | (ang < -180):
         return (360 - abs(ang))
     elif ang == 0: return ang + 1
     else:
         return ang

# 2B Scheduling functions
def check_prev_games(team,max_games,days_to_check):
    """ CHECKS IF A TEAM HAS PLAYED A CERTAIN NUMBER OF GAMES IN A
    CERTAIN NUMBER OF DAYS. USED IN CHECK ALL INTERVALS FUNCTION"""
    truth_list.clear()
    days_checked = 1
    check_str = re.compile(team)
    while days_checked < days_to_check + 1:
        check_date = (pd.to_datetime(current_date) - pd.to_timedelta(days_checked,"D")).strftime("%Y-%m-%d")
        if check_date not in games_by_date: break
        truth_list.append(any(filter(check_str.search,games_by_date[check_date])))
        days_checked += 1
    if sum(truth_list) < max_games:
        return True # means team passes check; has played below max games for number of days
    else:
        return False # fails check; has played too many games over interval

def check_all_intervals(team):
    """ CHECKS IF A TEAM HAS PLAYED A CERTAIN NUMBER OF GAMES IN A
    CERTAIN NUMBER OF DAYS.""" # intervals are taken from NHL schedule
    all_intervals_list = []
    all_intervals_list.append(check_prev_games(team,2,2))
    all_intervals_list.append(check_prev_games(team,3,4))
    all_intervals_list.append(check_prev_games(team,4,6))
    all_intervals_list.append(check_prev_games(team,5,7))
    return all(all_intervals_list)

def get_teams_from_game(game):
    """EXRTRACTS 3-LETTER ABBRVS FOR EACH TEAM FROM A AWY-HME
    STYLE GAME FROM A LIST"""
    str_extrct = re.compile("([A-Z]{3})-([A-Z]{3})")
    away_team = re.search(str_extrct,game)[1]
    home_team = re.search(str_extrct,game)[2]
    return away_team,home_team

def get_teams_from_list(list):
    """RETURNS HOME AND AWAY TEAMS FROM A GAME IN AWY-HME FORMAT"""
    game_to_check = random.choice(list)
    away_team,home_team = get_teams_from_game(game_to_check)
    return away_team, home_team

def get_games_from_list():
    """RETURNS HOME AND AWAY TEAMS FROM A GAME IN AWY-HME FORMAT, TAKING FROM
    PRIORITY OR DAILY LIST AS NECESSARY"""
    if priority_list:
        away_team,home_team = get_teams_from_list(priority_list)
        return away_team, home_team
    else:
        if daily_list:
            away_team,home_team = get_teams_from_list(daily_list)
            return away_team, home_team
        else: print("nonsense!") # and break out of loop

def end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic): #(EOD)
    """MAKES UPDATES AT THE END OF EACH DAY"""
    date = (pd.to_datetime(date) + pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")
    if list1:
        for game in list1:
            if game not in games_played_list:
                list1.remove(game)
        list2 += list1
        list1.clear() # at end of each day, move unplayed priority games from tomorrow prio list to prio for start of new day
    for team in nhl_info.index:
        if (team not in today_list) & (df.loc[team,"games_played"] > 0):
            df.loc[team,"rest_days"] += 1
    return date, list1, list2, df

def dynamic_updates(df = nhl_dynamic):
    """UPDATES DYNAMIC VARIABLES """
    if df.loc[away_team,"road_trip"] == 0:
        df.loc[away_team,"rt_first"] = home_team
    if (measure_distance(away_team,home_team) > 1396) & (df.loc[away_team,"long_road_trip"] == 0):
        df.loc[away_team,"long_road_trip"] = 1
    df.loc[home_team,"games_played"] += 1; df.loc[home_team,"homestand"] += 1
    df.loc[home_team,"road_trip"] = 0; df.loc[home_team,"long_road_trip"] = 0
    df.loc[away_team,"games_played"] += 1; df.loc[away_team,"road_trip"] += 1
    df.loc[away_team,"homestand"] = 0
    df.loc[home_team,"location"] = home_team; df.loc[away_team,"location"] = home_team # combine into one statement?
    df.loc[away_team,"rest_days"] = 0 ; df.loc[home_team,"rest_days"] = 0
    df.loc[away_team,"away_games"] += 1; df.loc[home_team,"home_games"] += 1
    if df.loc[home_team,"homestand"] == 1:
        df.loc[home_team,"rt_first"] = home_team
    return df

def long_distance_divisional(away_list, home_list):
    ldd_list = [] # don't schedule game if home team's neighbor is unavailable (reduces travel)
    """CHECKS EXCLUSIONS FOR DIVISION RIVALS FAR AWAY FROM EACH OTHER"""
    home_choices = home_list
    home_choices.remove(home_team)
    home_choices = home_choices[0]
    if (nhl_dynamic.loc[home_choices,"homestand"] > 9) | \
    ((nhl_dynamic.loc[home_choices,"home_games"] - nhl_dynamic.loc[home_choices,"away_games"]) > 7): # these exclusions are used throughout the program
        ldd_list.append(True)
    home_choices_str = re.compile(home_choices+"-") # away games for potential home team
    if (any(filter(home_choices_str.search,tomorrow_priority_list))) | (any(filter(home_choices_str.search,priority_list))) :
        ldd_list.append(True)
    return ldd_list

def home_away_clusters(): # used in pacplus_eastplus, non_prio_exclusions, reduced_nonprio, priority_list_exclusions
    """CHECKS AVAILABILITY OF CLUSTERMATES FOR HOME TEAM""" # prevents adding team as home on prio list if they can't play at home
    # i.e. don't schedule game if home clustermates can't be scheduled at home
    if home_team in clusters_list:
        home_clustermates = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
        home_clustermates.remove(home_team) # sets up list of clustermates of potential home team not including potential home team
        temp_clust_list = []
        for team in home_clustermates:
            clust_away_str = re.compile(team+"-")
            if (any(filter(clust_away_str.search,tomorrow_priority_list))) | (any(filter(clust_away_str.search,priority_list))):
                temp_clust_list.append(True)
                break
            if ((nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7)) & \
            (nhl_dynamic.loc[team,"home_games"] < 41):
                temp_clust_list.append(True)
                break
        home_clustermates.append(home_team)
        if any(temp_clust_list):
            return "exclusions_list"

def home_away_clusters_prio():
    """CHECKS AVAILABILITY OF CLUSTERMATES FOR HOME TEAM - ALSO ACCOUNTS FOR
    CURRENT DAY PRIO LIST UNLIKE OTHER VERSION OF THIS FUNCTION"""
    if home_team in clusters_list:
        home_clustermates = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
        home_clustermates.remove(home_team)
        temp_clust_list = []
        for team in home_clustermates:
            clust_away_str = re.compile(team+"-")
            if (any(filter(clust_away_str.search,tomorrow_priority_list))) | (any(filter(clust_away_str.search,priority_list))):
                temp_clust_list.append(True)
                break
            if ((nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7)) & \
            (nhl_dynamic.loc[team,"home_games"] < 41):
                temp_clust_list.append(True)
                break
        home_clustermates.append(home_team)
        if any(temp_clust_list):
            return "daily remove"

def dallas_northeast(): # used in non_prio_exclusions, min_noprio_exclusions, and reduced_nonprio
    """CHECKS AVAILABILITY OF DALLAS PLAYING AT MONTREAL, OTTAWA, OR BOSTON"""
    # only schedule against if other teams are also available to host
    northeast_check = north_east[:]
    northeast_check.remove(home_team)
    for team in northeast_check:
        clust_away_str = re.compile(team+"-")
        if (any(filter(clust_away_str.search,tomorrow_priority_list))) | (any(filter(clust_away_str.search,priority_list))):
            return "exclusions_list"
        if (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
            return "exclusions_list"

def pacmin_northcen(): # used in non_prio_exclusions, reduced_nonprio, and min_noprio_exclusions
    """CHECKS FOR AVAILABILIY OF GAMES OF WEST COAST/FL TEAMS PLAYING AT
    MINNESOTA AND WINNIPEG""" # only schedule against @ MIN/WIN if other team is also available to host
    north_cen_other = north_central[:]
    north_cen_other.remove(home_team)
    north_cen_other = north_cen_other[0]
    nco_away_str = re.compile(north_cen_other+"-")
    nco_home_str = re.compile("-"+north_cen_other)
    if (nhl_dynamic.loc[north_cen_other,"homestand"] > 9) | (any(filter(nco_away_str.search,tomorrow_priority_list))) | \
    (any(filter(nco_away_str.search,priority_list))) | ((nhl_dynamic.loc[north_cen_other,"home_games"] - nhl_dynamic.loc[north_cen_other,"away_games"]) > 7):
        return "exclusions_list"

def pacplus_eastplus(): # used in non_prio_exclusions, min_noprio_exclusions
    """CHECKS IF WEST COAST TEAM CAN PLAY AT EAST COAST TEAM""" # visitor needs to have at least 2 other nearby games to play
    pac_plus_away_str = re.compile(away_team+"-")
    if (not any(filter(pac_plus_away_str.search,tomorrow_priority_list))) & \
    (nhl_dynamic.loc[away_team,"location"] in east_plus): # prevents initiation of new cluster
        return "exclusions_list"
    if home_away_clusters() == "exclusions_list":
        return "exclusions_list"
    if ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 4):
        return "exclusions_list"
    east_plus_avail = []
    east_check = east_plus[:]
    east_check.remove(home_team)
    for team in east_check: # see which east teams can host
        team_str = re.compile(team+"-")
        if (any(filter(team_str.search,tomorrow_priority_list))) | (any(filter(team_str.search,priority_list))) | \
        (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
            east_check.remove(team)
            continue
        else:
            east_plus_avail.append(team)
    if len(east_plus_avail) < 2:
        return "exclusions_list"

def non_prio_exclusions():
    """CHECKS IF GAMES NOT ON PRIORITY LIST CAN BE SCHEDULED"""
    exclusions_list = []
    remove_home_abbrv = []; remove_home_str = []
    remove_away_abbrv= []; remove_away_str = []

    if check_all_intervals(away_team) == False: # away team can't play on current day. Remove all potential games from daily list and priority_list but add to tomorrow_priority_list
        return "remove_away_abbrv"
    if check_all_intervals(home_team) == False: # home team can't play on current day. Remove all potential  games from daily list and priority_list but add to tomorrow_priority_list
        return "remove_home_abbrv"
    if cant_host_df.loc[home_team,current_date] == 1: # only remove home games - team may be able to play on the road
        return "remove_home_str"
    if nhl_dynamic.loc[home_team,"homestand"] > 9: # not included in priority version
        return "remove_home_str"
    if nhl_dynamic.loc[away_team,"road_trip"] > 9: # not included in priority version
        return "remove_away_str"
    if (any(filter(opposite_away_str.search,tomorrow_priority_list))) | (any(filter(opposite_away_str.search,priority_list))):
        return "exclusions_list" # prevents team from being playing home game if away on PL/TPL and v/v
    if (any(filter(opposite_home_str.search,tomorrow_priority_list))) | (any(filter(opposite_home_str.search,priority_list))):
        return "exclusions_list"
    if (nhl_dynamic.loc[home_team,"home_games"] - nhl_dynamic.loc[home_team,"away_games"]) > 7: # not included in priority version - prevents imbalance of home/away games
        return "remove_home_str"
    if (nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 7: # not included in priority version
        return "remove_away_str"
    if (any(filter(away_str.search,tomorrow_priority_list))) & (away_team+"-"+home_team not in tomorrow_priority_list): # Away team is playing someone else on TPL
        return "exclusions_list"
    if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
        if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
         (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > 850): # away team played last night, > 850 miles away. # maybe in the future do function to remove all teams > 850  from current location to avoid looping over this multiple times
            return "exclusions_list"
        if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
        (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 850):  # home team played last night, >850 miles away. Can't host today
            return "remove_home_str"
    if ((nhl_dynamic.loc[away_team,"road_trip"] > 5) | ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 4)) & \
     (measure_distance(away_team,home_team) > 1396):
        if (home_team in clusters_list) | ((away_team in pac_plus) & (home_team in east_plus) \
        & (home_team not in clusters_list)):
            if (away_team+"-"+home_team not in tomorrow_priority_list) & (away_team+"-"+home_team not in priority_list): # Away team is too deep into road trip to trigger priority games
                return "exclusions_list"
    if ((nhl_dynamic.loc[away_team,"road_trip"] > 5) | ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 4)) & \
     (home_team not in clusters_list) & (nhl_info.loc[home_team,"Conf"] == "E") & \
     (away_team in central_west) & (1000 < measure_distance(away_team,home_team) < 1396):
        if (away_team+"-"+home_team not in tomorrow_priority_list) & (away_team+"-"+home_team not in priority_list): # Away team is too deep into road trip to trigger priority games
            return "exclusions_list"
    if (nhl_dynamic.loc[home_team,"homestand"] > 9) | ((nhl_dynamic.loc[home_team,"home_games"] - nhl_dynamic.loc[home_team,"away_games"]) > 7):
        # Home team needs to play on the road
        return "exclusions_list"
    if (nhl_dynamic.loc[away_team,"road_trip"] > 5) & (nhl_dynamic.loc[away_team,"long_road_trip"] == 1) & \
    (not(any(filter(away_str.search,tomorrow_priority_list)))): # Away team needs to play closer to home
        if measure_distance(away_team,home_team) > 1000:
            return "exclusions_list"
    if (nhl_dynamic.loc[away_team,"road_trip"] > 0) & ((angle3pt(home_team,away_team,nhl_dynamic.loc[away_team,"rt_first"]) > 120) & \
    (measure_distance(home_team,away_team) > 1000)): # keeps road trip in same general region of continent (reduces excessive travel)
        return "exclusions_list"
    if (angle3pt(nhl_dynamic.loc[away_team,"location"],away_team,home_team) > 90) & \
    (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > 1200): # Away team needs to play in same general direction
        return "exclusions_list"
    if (nhl_dynamic.loc[away_team,"long_road_trip"] == 1) & (nhl_dynamic.loc[away_team,"road_trip"] > 0) & \
    (measure_distance(nhl_dynamic.loc[away_team,"location"],away_team) < 1000): # prevents team from going far after being far and coming back closer
        if measure_distance(away_team,home_team) > 1200:
            return "exclusions_list"
    if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
        if any(filter(opposite_away_str.search,tomorrow_priority_list)): # away on tpl as home team
            if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) | \
            (measure_distance(home_team,away_team) > 1100):
                # prevents teams from playing non-prio game that would prevent them from playing prio game following day
                return "exclusions_list"
        if any(filter(home_str.search,tomorrow_priority_list)):
            if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))):
                return "exclusions_list"

    if (away_team in pac_minus) & (home_team in north_central): # see functions referenced in this block
        if pacmin_northcen() == "exclusions_list":
            return "exclusions_list"
    if (away_team == "DAL") & (home_team in north_east):
        if dallas_northeast() == "exclusions_list":
            return "exclusions_list"
    if (away_team in ["EDM","CAL"]) & (home_team in ["LAK","ANA"]):
        if any(long_distance_divisional(["EDM","CAL"], ["LAK","ANA"])):
            return "exclusions_list"
    if (away_team in ["LAK","ANA"]) & (home_team in ["EDM","CAL"]):
        if any(long_distance_divisional(["LAK","ANA"], ["EDM","CAL"])):
            return "exclusions_list"
    if (away_team in ["MON","OTT"]) & (home_team in ["FLA","TBL"]):
        if any(long_distance_divisional(["MON","OTT"], ["FLA","TBL"])):
            return "exclusions_list"
    if (away_team in ["FLA","TBL"]) & (home_team in ["MON","OTT"]):
        if any(long_distance_divisional(["FLA","TBL"], ["MON","OTT"])):
            return "exclusions_list"

    if (away_team in pac_plus) & (home_team in east_plus): # don't schedule pac_plus @ east_plus if there aren't at least 2 more east_plus teams available to be added to prio list
        if pacplus_eastplus() == "exclusions_list":
            return "exclusions_list"

    if 1000 < measure_distance(away_team,home_team) < 1396: # don't trigger new round of priority if has just finished one
        if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
            cen_west_str = re.compile(away_team+"-")
            if (not any(filter(cen_west_str.search,tomorrow_priority_list))) & \
            (nhl_dynamic.loc[away_team,"location"] in list(nhl_info[nhl_info["Conf"] == "E"].index)): # if location is in east but team is not on prio list it means they just finished a round of away prio games
                return "exclusions_list"
            if home_away_clusters() == "exclusions_list":
                return "exclusions_list"

        if (away_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & (home_team == "COL"): # applies to DET, CBJ, TOR, BUF, PIT
            for team in ["VGK","ARI"]: # in actual NHL schedule these teams can play one-off away games at COL. I chose to make these cluster situations
                clust_away_str = re.compile(team+"-")
                if (any(filter(clust_away_str.search,tomorrow_priority_list))) | (any(filter(clust_away_str.search,priority_list))):
                    return "exclusions_list"
                if ((nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7)) & \
                 (nhl_dynamic.loc[team,"home_games"] < 41):
                    return "exclusions_list"
            # should be redundant
            if (any(filter(away_str.search,tomorrow_priority_list))) | (any(filter(away_str.search,priority_list))):
                return "exclusions_list"

    if (measure_distance(away_team,home_team) > 1396) & (not (away_team in pac_plus) & (home_team in east_plus)): # don't schedule game if this will trigger priority games for home team's clustermates and they're on tpl as away team
        if home_away_clusters() == "exclusions_list":
            return "exclusions_list"

def reduced_nonprio():
    """CHECKS AVAILABILITY OF GAMES AT THE END OF THE SEASON. LESS RESTRICTIVE
    THAN NON_PRIO_EXCLUSIONS"""
    if check_all_intervals(away_team) == False: # away team can't play on current day. Remove their potential games from daily list and priority_list but add to tomorrow_priority_list
        return "exclusions_list"
    if check_all_intervals(home_team) == False: # home team can't play on current day. Remove their potential home games from daily list and priority_list but add to tomorrow_priority_list
        return "exclusions_list"
    if cant_host_df.loc[home_team,current_date] == 1: # home team can't host on current day. As above
        return "exclusions_list"
    if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
        if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
         (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > 1100): # away team played last night, > 850 miles away. # maybe in the future do function to remove all teams > 850  from current location to avoid looping over this multiple times
            return "exclusions_list"
        if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
        (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 1100):  # home team played last night, >850 miles away. Can't host today
            return "exclusions_list"
    if (any(filter(away_str.search,tomorrow_priority_list))) & (away_team+"-"+home_team not in tomorrow_priority_list):
        return "exclusions_list"
    if today_list:
        if (home_team in today_list) | (away_team in today_list):
            return "exclusions_list"
    if (any(filter(opposite_home_str.search,priority_list))) | (any(filter(opposite_home_str.search,tomorrow_priority_list))):
        return "exclusions_list"
    if (any(filter(opposite_away_str.search,priority_list))) | (any(filter(opposite_away_str.search,tomorrow_priority_list))):
        return "exclusions_list"
    if ((any(filter(away_str.search,priority_list))) | (any(filter(away_str.search,tomorrow_priority_list)))) & (away_team+"-"+home_team not in priority_list):
        return "exclusions_list"

    if (away_team in pac_plus) & (home_team in east_plus): # don't schedule pac_plus @ east_plus if there aren't at least 2 more east_plus teams available to be added to prio list
        if home_away_clusters() == "exclusions_list":
            return "exclusions_list"
    if (away_team in pac_minus) & (home_team in north_central):
        if pacmin_northcen() == "exclusions_list":
            return "exclusions_list"
    if (away_team == "DAL") & (home_team in north_east):
        if dallas_northeast() == "exclusions_list":
            return "exclusions_list"
    if (away_team in ["EDM","CAL"]) & (home_team in ["LAK","ANA"]):
        if any(long_distance_divisional(["EDM","CAL"], ["LAK","ANA"])):
            return "exclusions_list"
    if (away_team in ["LAK","ANA"]) & (home_team in ["EDM","CAL"]):
        if any(long_distance_divisional(["LAK","ANA"], ["EDM","CAL"])):
            return "exclusions_list"
    if (away_team in ["MON","OTT"]) & (home_team in ["FLA","TBL"]):
        if any(long_distance_divisional(["MON","OTT"], ["FLA","TBL"])):
            return "exclusions_list"
    if (away_team in ["FLA","TBL"]) & (home_team in ["MON","OTT"]):
        if any(long_distance_divisional(["FLA","TBL"], ["MON","OTT"])):
            return "exclusions_list"

    if 1000 < measure_distance(away_team,home_team) < 1396: # don't trigger new round of priority if has just finished one
        if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
            if home_away_clusters() == "exclusions_list":
                return "exclusions_list"

        if (away_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & (home_team == "COL"):
            for team in ["VGK","ARI"]:
                clust_away_str = re.compile(team+"-")
                if (any(filter(clust_away_str.search,tomorrow_priority_list))) | (any(filter(clust_away_str.search,priority_list))):
                    return "exclusions_list"
                if ((nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7)) & \
                (nhl_dynamic.loc[team,"home_games"] < 41):
                    return "exclusions_list"
            # should be redundant
            if (any(filter(away_str.search,tomorrow_priority_list))) | (any(filter(away_str.search,priority_list))):
                return "exclusions_list"

    if (measure_distance(away_team,home_team) > 1396) & (not (away_team in pac_plus) & (home_team in east_plus)): # don't schedule game if this will trigger priority games for home team's clustermates and they're on tpl as away team
        if home_away_clusters() == "exclusions_list":
            return "exclusions_list"

def npc_long_div(cluster_list, games_to_add, tomorrow_priority_list = tomorrow_priority_list):
   """REDUCES REPETITIVE CODE IN SCHEDULING GAMES BETWEEN LONG DISTANCE DIVISION RIVALS
   USED WITHIN NON_PRIO_CONSEQUENCES FUNCTION"""
   # prevents scheduling game if clustermate of home team can't play at home (roping them into home prio game)
   visiting = cluster_list
   visiting.remove(home_team)
   vis_hold = []
   for team in visiting:
       vis_away = re.compile(team+"-")
       if (any(filter(vis_away.search,priority_list))) | (any(filter(vis_away.search,tomorrow_priority_list))):
           vis_hold.append(team)
           continue
       if (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
           vis_hold.append(team)
           continue
   vis_sample = [team for team in visiting if team not in vis_hold]
   vis_list = [away_team+"-"+team for team in vis_sample if away_team+"-"+team in games_played_list]
   if len(vis_list) >= games_to_add:
       tomorrow_priority_list += random.sample(vis_list,games_to_add)
   elif vis_list: tomorrow_priority_list += vis_list
   return tomorrow_priority_list

def non_prio_consequences(tomorrow_priority_list = tomorrow_priority_list):
    """ADDS TO TOMORROW PRIORITY LIST BASED ON RELATIONSHIP OF TEAMS
    IN GAME BEING SCHEDULED """
    # the term "consequences" is used throughout to refer to games added to TPL as a result of a game being scheduled
    # because Winnipeg isn't near anyone else, anyone who travels far to play them should play Minnesota too
    if (away_team in pac_minus) & (home_team in north_central):
        if (away_team+"-"+home_team in games_played_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
            tomorrow_priority_list.append(away_team+"-"+home_team)
        north_cen_other = north_central[:]
        north_cen_other.remove(home_team)
        north_cen_other = north_cen_other[0]
        nco_away_str = re.compile(north_cen_other+"-")
        if (not any(filter(nco_away_str.search,tomorrow_priority_list))) & (not any(filter(nco_away_str.search,priority_list))):
            if (away_team+"-"+north_cen_other in games_played_list) & (away_team+"-"+north_cen_other not in tomorrow_priority_list):
                tomorrow_priority_list.append(away_team+"-"+north_cen_other)

    if measure_distance(away_team,home_team) > 1396: # away team vs. home clustermates added to TPL
        nhl_dynamic.loc[away_team,"long_road_trip"] = 1
        if home_team in clusters_list:
            home_cluster = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
            home_cluster.remove(home_team)
            for team in home_cluster:
                if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                    tomorrow_priority_list.append(away_team+"-"+team)
            home_cluster.append(home_team)
        if (away_team+"-"+home_team in games_played_list) & (away_team+"-"+home_team not in tomorrow_priority_list): # for some long distance divisional or intraconference games with two games in same location
            tomorrow_priority_list.append(away_team+"-"+home_team)

        if (away_team in pac_plus) & (home_team in east_plus) & \
        (home_team not in clusters_list): # west coast team playing at non-cluster E conf team (excludes CHI, WIN, MIN) who is not going to be on priority list as visitor.
           # see which non-cluster Eastern conference teams are available and add 2 or 3 to TPL depending on away team's road trip length
            east_sample = [team for team in east_plus if not team in clusters_list]
            east_sample.remove(home_team)
            east_hold = []
            for team in east_sample:
                east_away = re.compile(team+"-")
                if (any(filter(east_away.search,priority_list))) | (any(filter(east_away.search,tomorrow_priority_list))):
                    east_hold.append(team)
                    continue
                if (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
                    east_hold.append(team)
                    continue
            east_sample = [team for team in east_sample if not team in east_hold]
            east_nonclust_list = [away_team+"-"+team for team in east_sample if away_team+"-"+team in games_played_list]
            if len(east_nonclust_list) >= 3:
                if (nhl_dynamic.loc[away_team,"road_trip"] < 6) & ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) < 5):
                    tomorrow_priority_list += random.sample(east_nonclust_list,3)
                else: tomorrow_priority_list += random.sample(east_nonclust_list,2)
            elif east_nonclust_list: tomorrow_priority_list += east_nonclust_list

        if (away_team == "DAL") & (home_team in north_east): # special behavior for Dallas against MON, OTT, BOS. Should play all 3 on same road trip
            northeast_others = north_east[:]
            northeast_others.remove(home_team)
            for team in northeast_others:
                if ("DAL"+"-"+team in games_played_list) & ("DAL"+"-"+team not in tomorrow_priority_list):
                    tomorrow_priority_list.append("DAL"+"-"+team)

    if 1000 < measure_distance(away_team,home_team) < 1396:
        if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
            # minimize travel to have COL, MIN, or WIN play New York teams together because they're so close to each other
            if home_team in clusters_list:
                home_cluster = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                home_cluster.remove(home_team)
                for team in home_cluster:
                    if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                        tomorrow_priority_list.append(away_team+"-"+team)
                home_cluster.append(home_team)

            else: # same routine for non-cluster East conf teams
                east_sample = [team for team in list(nhl_info[nhl_info["Conf"] == "E"].index) if not team in clusters_list]
                east_sample.remove(home_team)
                east_hold = []
                for team in east_sample:
                    east_away = re.compile(team+"-")
                    if (any(filter(east_away.search,priority_list))) | (any(filter(east_away.search,tomorrow_priority_list))):
                        east_hold.append(team)
                        continue
                    if (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
                        east_hold.append(team)
                        continue
                east_sample = [team for team in east_sample if not team in east_hold]
                east_nonclust_list = [away_team+"-"+team for team in east_sample if away_team+"-"+team in games_played_list]
                if len(east_nonclust_list) >= 3:
                    if (nhl_dynamic.loc[away_team,"road_trip"] < 6) & ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) < 5):
                        tomorrow_priority_list += random.sample(east_nonclust_list,2)
                    else: tomorrow_priority_list += random.sample(east_nonclust_list,1)
                elif east_nonclust_list: tomorrow_priority_list += east_nonclust_list

        if (away_team in ["EDM","CAL"]) & (home_team in ["LAK","ANA"]): # EDM or CAL play a couple games in region of southern cal
            tomorrow_priority_list = npc_long_div(clusters["CALI"] + ["ARI","VGK","COL"], 2, tomorrow_priority_list)

        if (away_team in ["LAK","ANA"]) & (home_team in ["EDM","CAL"]): # LAK or ANA play another game if traveling to Alberta
            socal_visiting = clusters["NW"][:]
            socal_visiting.remove(home_team)
            socal_vis_hold = []
            for team in socal_visiting:
                socal_vis_away = re.compile(team+"-")
                if (any(filter(socal_vis_away.search,priority_list))) | (any(filter(socal_vis_away.search,tomorrow_priority_list))):
                    socal_vis_hold.append(team)
                    continue
                if (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
                    socal_vis_hold.append(team)
                    continue
            socal_vis_sample = [team for team in socal_visiting if team not in socal_vis_hold]
            socal_vis_list = [away_team+"-"+team for team in socal_vis_sample if away_team+"-"+team in games_played_list]
            if len(socal_vis_list) >= 1:
                tomorrow_priority_list += random.sample(socal_vis_list,1)

        if (away_team in ["MON","OTT"]) & (home_team in ["FLA","TBL"]):
            ont_visiting = clusters["SE"] + ["NSH"]
            ont_visiting.remove(home_team)
            ont_vis_hold = []
            for team in ont_visiting:
                ont_vis_away = re.compile(team+"-")
                if (any(filter(ont_vis_away.search,priority_list))) | (any(filter(ont_vis_away.search,tomorrow_priority_list))):
                    ont_vis_hold.append(team)
                    continue
                if (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
                    ont_vis_hold.append(team)
                    continue
            ont_vis_sample = [team for team in ont_visiting if team not in ont_vis_hold]
            ont_vis_list = [away_team+"-"+team for team in ont_vis_sample if away_team+"-"+team in games_played_list]
            if ont_vis_list: tomorrow_priority_list += ont_vis_list

        if (away_team in ["FLA","TBL"]) & (home_team in ["MON","OTT"]):
            tomorrow_priority_list = npc_long_div(["MON","OTT","TOR","BUF"],2,tomorrow_priority_list)

        if (away_team in list(nhl_info[nhl_info["Conf"] =="E"].index)) & (home_team == "COL"):
            for team in ["ARI","VGK"]:
                if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                    tomorrow_priority_list.append(away_team+"-"+team)

        # Purpose of this is if visitor has spare game against cluster team (because of multiple awy-hme matchups of intraconference teams),
        # try to play other games nearby or close to home to make good use of road trip
        # - try to prevent them from going somewhere way out of the way
        if (nhl_dynamic.loc[away_team,"long_road_trip"] == 1) & (nhl_dynamic.loc[away_team,"road_trip"] < 3) & \
        (nhl_dynamic.loc[away_team,"location"] in clusters_list) & (measure_distance(away_team,home_team) > 1396) & \
        (not any(filter(away_str.search,tomorrow_priority_list))):
            # first try to add teams within 1000 miles
            within1000_sample = []
            within1000_hold = []
            for team in nhl_info.index:
                if measure_distance(team,away_team) < 1000:
                    within1000_sample.append(team)
            for team in within1000_sample:
                within1000_away = re.compile(team+"-")
                if (any(filter(within1000_away.search,tomorrow_priority_list))) | (nhl_dynamic.loc[team,"homestand"] > 8) | \
                ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 6):
                    within1000_hold.append(team)
            within1000_sample = [team for team in within1000_sample if team not in within1000_hold]
            within1000_list = [away_team+"-"+team for team in within1000_sample if away_team+"-"+team in games_played_list]
            # teams within 500 miles of away team's home
            home500_sample = []
            home500_hold = []
            for team in nhl_info.index:
                if measure_distance(team,away_team) < 500:
                    home500_sample.append(team)
            for team in home500_sample:
                home500_away = re.compile(team+"-")
                if (any(filter(home500_away.search,tomorrow_priority_list))) | (nhl_dynamic.loc[team,"homestand"] > 8) | \
                ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 6):
                    home500_hold.append(team)
            home500_sample = [team for team in home500_sample if not team in home500_hold]
            home500_list = [away_team+"-"+team for team in home500_sample if away_team+"-"+team in games_played_list]
            if len(within1000_list) >= 2:
                tomorrow_priority_list += random.sample(within1000_list,2)
            elif len(within1000_list) == 1:
                tomorrow_priority_list += within1000_list
                if len(home500_list) >= 1: tomorrow_priority_list += random.sample(home500_list,1)
            else:
                # no games available within 1000 games
                if len(home500_list) >= 2:
                    tomorrow_priority_list += random.sample(home500_list,2)
                else:
                    if home500_list:
                        tomorrow_priority_list += home500_list
    return tomorrow_priority_list

def priority_exclusions():
    """CHECKS AVAILABILIY OF SCHEDULING GAMES FOR TEAMS WITH LOW GAMES PLAYED
    AND ON PRIORITY LIST AT END OF SEASON"""
    if check_all_intervals(away_team) == False: # home team can't play on current day. Remove their potential home games from daily list and priority_list but add to tomorrow_priority_list
        return "pl remove"
    if check_all_intervals(home_team) == False: # home team can't play on current day. Remove their potential home games from daily list and priority_list but add to tomorrow_priority_list
        return "pl remove"
    if cant_host_df.loc[home_team,current_date] == 1: # home team can't host on current day. As above
        return "pl remove"
    if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
        if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
         (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > 1100): # away team played last night, > 850 miles away. # maybe in the future do function to remove all teams > 850  from current location to avoid looping over this multiple times
            return "pl remove"
        if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
        (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 1100):  # home team played last night, >850 miles away. Can't host today
            return "pl remove"
    if today_list: # don't schedule another game if team has a game scheduled on current day.
        if (home_team in today_list) | (away_team in today_list):
            return "pl remove"
    if (any(filter(opposite_home_str.search,priority_list))) | (any(filter(opposite_home_str.search,tomorrow_priority_list))):
        return "pl remove"
    if (any(filter(opposite_away_str.search,priority_list))) | (any(filter(opposite_away_str.search,tomorrow_priority_list))):
        return "pl remove"

def priority_list_exclusions(dist = 850): #
    """CHECKS AVAILABILITY OF GAMES CHOSEN FROM PRIORITY LIST """
    if check_all_intervals(away_team) == False: # away team can't play on current day. Remove their potential games from daily list and priority_list but add to tomorrow_priority_list
        return "pl remove"
    if check_all_intervals(home_team) == False: # home team can't play on current day. Remove their potential home games from daily list and priority_list but add to tomorrow_priority_list
        return "pl remove"
    if cant_host_df.loc[home_team,current_date] == 1: # home team can't host on current day. As above
        return "pl remove"
    if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
        if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
         (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > dist): # away team played last night, > 850 miles away. # maybe in the future do function to remove all teams > 850  from current location to avoid looping over this multiple times
            return "pl remove"
        if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
        (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > dist):  # home team played last night, >850 miles away. Can't host today
            return "pl remove"
    if today_list:
        if (home_team in today_list) | (away_team in today_list):
            return "pl remove"
    if (any(filter(opposite_home_str.search,priority_list))) | (any(filter(opposite_home_str.search,tomorrow_priority_list))):
        return "pl remove"
    if (any(filter(opposite_away_str.search,priority_list))) | (any(filter(opposite_away_str.search,tomorrow_priority_list))):
        return "pl remove"

        if (away_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & (home_team == "COL"):
            for team in ["VGK","ARI"]:
                print(team)
                clust_away_str = re.compile(team+"-")
                if (any(filter(clust_away_str.search,tomorrow_priority_list))) | (any(filter(clust_away_str.search,priority_list))):
                    return "pl remove"

def min_no_prio_longdiv(away_list,home_list):
    """DETERMINES IF LONG DISTANCE DIVISION GAME CAN BE
    SCHEDULED FOR TEAM WITH LOW GP BUT NOT ON PRIORITY LIST"""
    mnpl_list = []
    home_choices = home_list
    home_choices.remove(home_team)
    home_choices = home_choices[0]
    if ((nhl_dynamic.loc[home_choices,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7)) & \
    (nhl_dynamic.loc[home_choices,"home_games"] < 41):
        mnpl_list.append(True)
    home_choices_str = re.compile(home_choices+"-")
    if (any(filter(home_choices_str.search,tomorrow_priority_list))) | (any(filter(home_choices_str.search,priority_list))):
        mnpl_list.append(True)
    if (any(filter(opposite_away_str.search,tomorrow_priority_list))) | (any(filter(opposite_away_str.search,priority_list))):
        mnpl_list.append(True)
    return mnpl_list

def min_noprio_exclusions():
    """DETERMINES IF GAMES FOR TEAMS WITH LOW GP BUT NOT ON PRIORITY
    LIST CAN BE SCHEDULED """
    if check_all_intervals(away_team) == False:
        return "remove_away_abbrv"
    if check_all_intervals(home_team) == False: # home team can't play on current day. Remove their potential home games from daily list and priority_list but add to tomorrow_priority_list
        return "remove_home_abbrv"
    if cant_host_df.loc[home_team,current_date] == 1: # only remove home games involving min_gp team
        return "remove_home_str"
    if nhl_dynamic.loc[home_team,"homestand"] > 9: # not included in priority version
        return "remove_home_str"
    if nhl_dynamic.loc[away_team,"road_trip"] > 9: # not included in priority version
        return "remove_away_str"
    if ((nhl_dynamic.loc[home_team,"home_games"] - nhl_dynamic.loc[home_team,"away_games"]) > 7): # prevents home-away imbalance
        return "remove_home_str"
    if ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 7): # prevents home-away imbalance
        return "remove_away_str"
    if (any(filter(away_str.search,tomorrow_priority_list))) & (away_team+"-"+home_team not in tomorrow_priority_list): # away team needs to play someone else on TPL
        return "mnp_remove"
    if (any(filter(away_str.search,priority_list))) & (away_team+"-"+home_team not in tomorrow_priority_list): # away team needs to play someone else on priority list
        return "mnp_remove"
    if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
        if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
         (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > 850): # away team played last night, > 850 miles away. # maybe in the future do function to remove all teams > 850  from current location to avoid looping over this multiple times
            return "mnp_remove"
        if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
        (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 850):  # home team played last night, >850 miles away. Can't host today
            return "remove_home_str"
    if ((nhl_dynamic.loc[away_team,"road_trip"] > 5) | ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 7)) & \
    (measure_distance(away_team,home_team) > 1396):
        if (home_team in clusters_list) | ((away_team in pac_plus) & (home_team in east_plus)) & \
        (home_team not in clusters_list):
            if (away_team+"-"+home_team not in tomorrow_priority_list) & (away_team+"-"+home_team not in priority_list): # prevents road trip or H-A imbalance from getting too big...
                 # don't schedule a game that triggers multiple road games for away team
                return "mnp_remove"
    if ((nhl_dynamic.loc[away_team,"road_trip"] > 5) | ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 7)) & \
     (home_team not in clusters_list) & (nhl_info.loc[home_team,"Conf"] == "E") & \
     (away_team in central_west) & (1000 < measure_distance(away_team,home_team) < 1396):
        if (away_team+"-"+home_team not in tomorrow_priority_list) & (away_team+"-"+home_team not in priority_list): # same idea, different condition based on matchup
            return "mnp_remove"
    if ((nhl_dynamic.loc[home_team,"homestand"] > 9) | ((nhl_dynamic.loc[home_team,"home_games"] - nhl_dynamic.loc[home_team,"away_games"]) > 7)) & \
    (nhl_dynamic.loc[home_team,"home_games"] < 41): # home team can't play at home because of h-a imbalance or road trip length
        return "remove_home_str"
    if (nhl_dynamic.loc[away_team,"road_trip"] > 5) & (nhl_dynamic.loc[away_team,"long_road_trip"] == 1) & \
    ((not(any(filter(away_str.search,tomorrow_priority_list)))) | (not(any(filter(away_str.search,priority_list))))):
        if measure_distance(away_team,home_team) > 850: # makes away team play close to home if traveled far on current road trip
            return "mnp_remove"
    if (nhl_dynamic.loc[away_team,"long_road_trip"] == 1 ) & (measure_distance(nhl_dynamic.loc[away_team,"location"],away_team) < 1000):
        if measure_distance(away_team,home_team) > 850: # makes away team play close to home if traveled far on current road trip
            return "mnp_remove"
    if (nhl_dynamic.loc[away_team,"road_trip"] > 0) & ((angle3pt(home_team,away_team,nhl_dynamic.loc[away_team,"rt_first"]) > 120) & \
    (measure_distance(home_team,away_team) > 1100)) & (nhl_dynamic.loc[away_team,"rest_days"] < 5) & (nhl_dynamic.loc[away_team,"away_games"] < 39):
    # keeps away team from having road trip going all over the continent
        return "mnp_remove"
    if (angle3pt(nhl_dynamic.loc[away_team,"location"],away_team,home_team) > 90) & \
    (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > 1200) & (nhl_dynamic.loc[away_team,"location"] != away_team) & \
    (nhl_dynamic.loc[away_team,"rest_days"] < 5) & (nhl_dynamic.loc[away_team,"away_games"] < 39):
    # keeps away team from having road trip going all over the continent
        return "mnp_remove"
    if (nhl_dynamic.loc[away_team,"long_road_trip"] == 1) & (nhl_dynamic.loc[away_team,"road_trip"] > 0) & \
    (measure_distance(nhl_dynamic.loc[away_team,"location"],away_team) < 1000): # prevents team from going far after being far and coming back closer
        if measure_distance(away_team,home_team) > 1200:
            return "mnp_remove"
    if (any(filter(opposite_home_str.search,tomorrow_priority_list))) | (any(filter(opposite_home_str.search,priority_list))) : # home team is away on tpl
        return "mnp_remove"
    if tomorrow_priority_list:
        if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
            if any(filter(opposite_away_str.search,tomorrow_priority_list)): # away on tpl as home team
                if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) | \
                (measure_distance(home_team,away_team) > 850):
                    return "mnp_remove"
            if any(filter(home_str.search,tomorrow_priority_list)): # if home team is home on tpl
                if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))):
                    return "mnp_remove"
    if (any(filter(opposite_away_str.search,tomorrow_priority_list))) | (any(filter(opposite_away_str.search,priority_list))):
        return "mnp_remove"
    if (any(filter(opposite_home_str.search,tomorrow_priority_list))) | (any(filter(opposite_home_str.search,priority_list))):
        return "mnp_remove"

    if (away_team in pac_minus) & (home_team in north_central): # see functions referenced in this function
        if pacmin_northcen() == "exclusions_list":
            return "mnp_remove"
    if (away_team == "DAL") & (home_team in north_east):
        if dallas_northeast() == "exclusions_list":
            return "mnp_remove"
    if (away_team in ["EDM","CAL"]) & (home_team in ["LAK","ANA"]):
        if any(min_no_prio_longdiv(["EDM","CAL"],["LAK","ANA"])):
            return "mnp_remove"
    if (away_team in ["LAK","ANA"]) & (home_team in ["EDM","CAL"]):
        if any(min_no_prio_longdiv(["LAK","ANA"],["EDM","CAL"])):
            return "mnp_remove"
    if (away_team in ["MON","OTT"]) & (home_team in ["FLA","TBL"]):
        if any(min_no_prio_longdiv(["MON","OTT"],["FLA","TBL"])):
            return "mnp_remove"
    if (away_team in ["FLA","TBL"]) & (home_team in ["MON","OTT"]):
        if any(min_no_prio_longdiv(["FLA","TBL"],["MON","OTT"])):
            return "mnp_remove"
    if (away_team in pac_plus) & (home_team in east_plus):
        if pacplus_eastplus() == "exclusions_list":
            return "mnp_remove"

    if 1000 < measure_distance(away_team,home_team) < 1396:
        if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
            cen_west_str = re.compile(away_team+"-")
            if (not any(filter(cen_west_str.search,tomorrow_priority_list))) & \
            (nhl_dynamic.loc[away_team,"location"] in list(nhl_info[nhl_info["Conf"] == "E"].index)):
                return "mnp_remove"
            if (not any(filter(cen_west_str.search,priority_list))) & \
            (nhl_dynamic.loc[away_team,"location"] in list(nhl_info[nhl_info["Conf"] == "E"].index)):
                return "mnp_remove"
            if home_away_clusters_prio() == "daily remove":
                return "mnp_remove"

        if (away_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & (home_team == "COL"):
            for team in ["VGK","ARI"]:
                clust_away_str = re.compile(team+"-")
                if (any(filter(clust_away_str.search,tomorrow_priority_list))) | (any(filter(clust_away_str.search,priority_list))):
                    return "mnp_remove"
                if ((nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7)) & \
                (nhl_dynamic.loc[team,"home_games"] < 41):
                    return "mnp_remove"

    if (measure_distance(away_team,home_team) > 1396) & (not (away_team in pac_plus) & (home_team in east_plus)): # don't schedule game if this will trigger priority games for home team's clustermates and they're on tpl as away team
        if home_away_clusters_prio() == "daily remove":
            return "mnp_remove"

def allstar_triggers():
    """PREVENTS CREATION OF NEW PRIORITY GAMES IN THE LEAD-UP TO THE ALL STAR GAME"""
    if (away_team in pac_minus) & (home_team in north_central) & (measure_distance(away_team,home_team) < 1396):
        return "daily remove"
    if (measure_distance(away_team,home_team) > 1396):
        return "daily remove"
    if (away_team in pac_plus) & (home_team in east_plus):
        return "daily remove"
    if (len(set(before_asg)) > 14) & ("2023-01-29" < current_date < "2023-02-03"):
        if (away_team not in before_asg) | (home_team not in before_asg):
            return "daily remove"
    if 1000 < measure_distance(away_team,home_team) < 1396:
        if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
            return "daily remove"
    if (away_team in ["EDM","CAL"]) & (home_team in ["LAK","ANA"]):
        return "daily remove"
    if (away_team in ["LAK","ANA"]) & (home_team in ["EDM","CAL"]):
        return "daily remove"
    if (away_team in ["MON","OTT"]) & (home_team in ["FLA","TBL"]):
        return "daily remove"
    if (away_team in ["FLA","TBL"]) & (home_team in ["MON","OTT"]):
        return "daily remove"
    if (away_team in list(nhl_info[nhl_info["Conf"] =="E"].index)) & (home_team == "COL"):
        return "daily remove"
    if (away_team == "DAL") & (home_team in north_east):
        return "daily remove"
    if (any(filter(opposite_away_str.search,tomorrow_priority_list))) | (any(filter(opposite_away_str.search,priority_list))):
        return "daily remove"
    if (any(filter(opposite_home_str.search,tomorrow_priority_list))) | (any(filter(opposite_home_str.search,priority_list))):
        return "daily remove"

def long_div_after_asb(away_list,home_list):
    """DEALS WITH LONG DISTANCE DIVISION RIVALS IN WEEK AFTER ALL STAR BREAK"""
    home_choices = home_list
    home_choices.remove(home_team)
    home_choices = home_choices[0]
    if home_choices in before_asg: # don't schedule game if home team's neighbor is on bye after ASB
        return "daily remove"
    home_choices_str = re.compile(home_choices+"-")
    if (any(filter(home_choices_str.search,tomorrow_priority_list))) | (any(filter(home_choices_str.search,priority_list))):
        return "daily remove"

def mpg_exclusions():
    """REDUCES REPETITIVE CODE DEALING WITH FOR LOOPS OF MIN_PRIO_GAMES"""
    if check_all_intervals(away_team) == False:
        if away_team == min_prio_team: return "break"
        else: return "continue"
    if check_all_intervals(home_team) == False: # home team can't play on current day. Remove their potential home games from daily list, MPL, and priority_list but add to TPL
        if home_team == min_prio_team: return "break"
        else: return "continue"
    if cant_host_df.loc[home_team,current_date] == 1: # only remove home games involving min_gp team
        if home_team == min_prio_team: return "break"
        else: return "continue"
    if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
        if (any(filter(away_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
        (measure_distance(nhl_dynamic.loc[away_team,"location"],home_team) > 850): # away team played last night, > 850 miles away. # maybe in the future do function to remove all teams > 850  from current location to avoid looping over this multiple times
            if away_team == min_prio_team: return "break"
            else: return "continue"
        if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
        (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 850):  # home team played last night, >850 miles away. Can't host today
            if home_team == min_prio_team: return "break"
            else: return "continue"
    if ((nhl_dynamic.loc[home_team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7)) & \
     (away_team+"-"+home_team not in priority_list) & (nhl_dynamic.loc[home_team,"home_games"] < 41): # home team can't host if in the middle of long road trip or if maxed out homestand
        if home_team == min_prio_team: return "break"
        else: return "continue"
    if ((nhl_dynamic.loc[away_team,"road_trip"] > 5) | ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 4)) & \
    (home_team in clusters_list) & (measure_distance(away_team,home_team) > 1396):
        away_str = re.compile(away_team+"-")
        if (not(any(filter(away_str.search,priority_list)))) & (not(any(filter(away_str.search,tomorrow_priority_list)))):
            return "continue"
    if ((nhl_dynamic.loc[away_team,"road_trip"] > 5) | ((nhl_dynamic.loc[away_team,"away_games"] - nhl_dynamic.loc[away_team,"home_games"]) > 4)) & \
    (home_team not in clusters_list) & \
    (nhl_info.loc[home_team,"Conf"] == "E") & (away_team in central_west) & (1000 < measure_distance(away_team,home_team) < 1396):
        away_str = re.compile(away_team+"-")
        if (not(any(filter(away_str.search,priority_list)))) & (not(any(filter(away_str.search,tomorrow_priority_list)))):
            return "continue"
    if (any(filter(opposite_away_str.search,tomorrow_priority_list))) | (any(filter(opposite_away_str.search,priority_list))):
        return "continue"
    if (any(filter(opposite_home_str.search,tomorrow_priority_list))) | (any(filter(opposite_home_str.search,priority_list))):
        return "continue"

def pacplus_eastconf(tomorrow_priority_list = tomorrow_priority_list):
    """CONSEQUENCES IF WEST COAST TEAM IS SCHEDULED TO PLAY AGAINST
    EASTERN CONFERENCE TEAM AT END OF SEASON"""
    if ((away_team in pac_plus) & (home_team in east_plus)) & \
    (home_team not in clusters_list): # west coast team playing at non-cluster E conf team or CHI
        east_sample = [team for team in east_plus if not team in clusters_list]
        east_sample.remove(home_team)
        east_hold = []
        for team in east_sample:
            east_away = re.compile(team+"-")
            if (any(filter(east_away.search,priority_list))) | (any(filter(east_away.search,tomorrow_priority_list))):
                east_hold.append(team)
                continue
            if (nhl_dynamic.loc[team,"homestand"] > 9) | ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"home_games"]) > 7):
                east_hold.append(team)
                continue
        east_sample = [team for team in east_sample if team not in east_hold]
        east_nonclust_list = [away_team+"-"+team for team in east_sample if away_team+"-"+team in games_played_list]
        if east_nonclust_list: tomorrow_priority_list += east_nonclust_list # finish off these games - no more east coast road trips for west coast teams
        return tomorrow_priority_list

def generate_strings():
    """RETURNS STRINGS USED IN REGULAR EXPRESSIONS THROUGHOUT THE PROGRAM"""
    away_str = re.compile(away_team+"-"); home_str = re.compile("-"+home_team)
    away_abbrv_str = re.compile(away_team); home_abbrv_str = re.compile(home_team)
    opposite_home_str = re.compile(home_team+"-"); opposite_away_str = re.compile("-"+away_team)
    return away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str

def scheduling_routine_npc(season_games_list = season_games_list, games_played_list = games_played_list, \
priority_list = priority_list, daily_list = daily_list, games_by_date = games_by_date, \
tomorrow_priority_list = tomorrow_priority_list, today_list = today_list, nhl_dynamic = nhl_dynamic):
  """SCHEDULES GAMES AND MAKES UPDATES - FOR NON-PRIORITY GAMES"""
  # NPC refers to non-prio consequences
  season_games_list.append(game_to_check)
  games_played_list.remove(game_to_check)
  if current_date not in games_by_date.keys():
      games_by_date[current_date] = [game_to_check]
  else: games_by_date[current_date].append(game_to_check)
  if game_to_check in tomorrow_priority_list: tomorrow_priority_list.remove(game_to_check)

  today_list.append(away_team); today_list.append(home_team)
  nhl_dynamic = dynamic_updates(df = nhl_dynamic)
  tomorrow_priority_list = non_prio_consequences(tomorrow_priority_list = tomorrow_priority_list)

  daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
  daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
  if any(filter(home_abbrv_str.search,priority_list)):
      home_removed = [game for game in priority_list if re.search(home_abbrv_str,game)]
      priority_list = [game for game in priority_list if not re.search(home_abbrv_str,game)]
      if home_removed:
          for game in home_removed:
              if game in games_played_list: tomorrow_priority_list.append(game)

  if any(filter(away_abbrv_str.search,priority_list)):
      away_removed = [game for game in priority_list if re.search(away_abbrv_str,game)]
      priority_list = [game for game in priority_list if not re.search(away_abbrv_str,game)]
      if away_removed:
          for game in away_removed:
              if game in games_played_list: tomorrow_priority_list.append(game)
  return season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic

def scheduling_routine_mpg(season_games_list = season_games_list, games_played_list = games_played_list, \
priority_list = priority_list, daily_list = daily_list, games_by_date = games_by_date, \
tomorrow_priority_list = tomorrow_priority_list, today_list = today_list, nhl_dynamic = nhl_dynamic):
    """SCHEDULES GAMES AND MAKES UPDATES - FOR PRIORITY GAMES OF TEAMS WITH LOW GAMES PLAYED"""
    #MPG stands for minimum priority games. Games involving min GP team on priority list
    season_games_list.append(game_to_check)
    games_played_list.remove(game_to_check)
    priority_list.remove(game_to_check)
    daily_list.remove(game_to_check)
    if current_date not in games_by_date.keys():
        games_by_date[current_date] = [game_to_check]
    else: games_by_date[current_date].append(game_to_check)
    if game_to_check in tomorrow_priority_list: tomorrow_priority_list.remove(game_to_check)

    today_list.append(away_team); today_list.append(home_team)
    nhl_dynamic = dynamic_updates(df = nhl_dynamic)

    daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
    daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
    if any(filter(home_abbrv_str.search,priority_list)):
        home_removed = [game for game in priority_list if re.search(home_abbrv_str,game)]
        priority_list = [game for game in priority_list if not re.search(home_abbrv_str,game)]
        if home_removed:
            for game in home_removed:
                if game in games_played_list: tomorrow_priority_list.append(game)

    if any(filter(away_abbrv_str.search,priority_list)):
        away_removed = [game for game in priority_list if re.search(away_abbrv_str,game)]
        priority_list = [game for game in priority_list if not re.search(away_abbrv_str,game)]
        if away_removed:
            for game in away_removed:
                if game in games_played_list: tomorrow_priority_list.append(game)
    return season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic

def scheduling_routine_prio(season_games_list = season_games_list, games_played_list = games_played_list, \
priority_list = priority_list, daily_list = daily_list, games_by_date = games_by_date, \
tomorrow_priority_list = tomorrow_priority_list, today_list = today_list, nhl_dynamic = nhl_dynamic):
  """SCHEDULES GAMES AND MAKES UPDATES - FOR PRIORITY GAMES""" # when not involving min GP team
  season_games_list.append(game_to_check)
  games_played_list.remove(game_to_check)
  if current_date not in games_by_date.keys():
      games_by_date[current_date] = [game_to_check]
  else: games_by_date[current_date].append(game_to_check)
  if game_to_check in tomorrow_priority_list: tomorrow_priority_list.remove(game_to_check)
  daily_list.remove(game_to_check)
  today_list.append(away_team); today_list.append(home_team)

  nhl_dynamic = dynamic_updates(df = nhl_dynamic)

  daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
  daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
  return season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic

def scheduling_routine_mph(season_games_list = season_games_list, games_played_list = games_played_list, \
priority_list = priority_list, daily_list = daily_list, games_by_date = games_by_date, \
tomorrow_priority_list = tomorrow_priority_list, today_list = today_list, nhl_dynamic = nhl_dynamic):
    """SCHEDULES GAMES AND MAKES UPDATES - HOME GAMES NOT ON PRIORITY LIST FOR
    TEAMS WITH LOW GP, ON PRIORITY LIST, BUT COULDN'T SCHEDULE PRIORITY GAMES"""
    season_games_list.append(game_to_check)
    games_played_list.remove(game_to_check)
    daily_list.remove(game_to_check)
    if current_date not in games_by_date.keys():
        games_by_date[current_date] = [game_to_check]
    else: games_by_date[current_date].append(game_to_check)
    if game_to_check in tomorrow_priority_list: tomorrow_priority_list.remove(game_to_check)

    today_list.append(away_team); today_list.append(home_team); print("Today list: ", today_list, "(Line 1846)")
    nhl_dynamic = dynamic_updates(df = nhl_dynamic)

    daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
    daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
    if any(filter(home_abbrv_str.search,priority_list)):
        home_removed = [game for game in priority_list if re.search(home_abbrv_str,game)]
        priority_list = [game for game in priority_list if not re.search(home_abbrv_str,game)]
        if home_removed:
            for game in home_removed:
                if game in games_played_list: tomorrow_priority_list.append(game)

    if any(filter(away_abbrv_str.search,priority_list)):
        away_removed = [game for game in priority_list if re.search(away_abbrv_str,game)]
        priority_list = [game for game in priority_list if not re.search(away_abbrv_str,game)]
        if away_removed:
            for game in away_removed:
                if game in games_played_list: tomorrow_priority_list.append(game)
    return season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic

def long_div_season_end(cluster_list, tomorrow_priority_list = tomorrow_priority_list):
    """REDUCES REPETITIVE CODE FOR SCHEDULING GAMES BETWEEN TEAMS FAR APART
    AND IN SAME DIVISION WITH SPECIAL CHANGES FOR END OF SEASON PROCEDURE"""
    visiting = cluster_list
    visiting.remove(home_team)
    for team in visiting:
        vis_away = re.compile(team+"-")
        if (any(filter(vis_away.search,priority_list))) | (any(filter(vis_away.search,tomorrow_priority_list))):
            visiting.remove(team)
            continue
        if (nhl_dynamic.loc[team,"homestand"] > 9) & (nhl_dynamic.loc[team,"away_games"] < 41):
            visiting.remove(team)
            continue
    vis_list = [away_team+"-"+team for team in visiting if away_team+"-"+team in games_played_list]
    if vis_list: tomorrow_priority_list += vis_list
    return tomorrow_priority_list

def check_team(team):
    """USED TO CHECK SCHEDULE FOR INDIVIDUAL TEAMS AFTER THE PROGRAM HAS BEEN RUN"""
    games_list = pd.Series(season_games_list)
    check_df = pd.DataFrame(games_list, columns = ['games'])
    check_df[["Away","Home"]] = check_df.games.str.split("-",expand=True)
    team_df = check_df[(check_df.Away == team) | (check_df.Home == team)]
    team_str = re.compile(team)
    team_games = [game for game in season_games_list if re.search(team_str,game)]
    return team_games

### ***** PART 3A ***** ####
### Seed schedule with first two games on opening night###
# first game of season involves cup winner hosting team in same division
# if cup winner arena not available, move on to runner up
# this program also allows for trying semi-finalists if both winner and runner-up are unavailable
home_team = ""
cup_winner =  nhl_info[nhl_info["Last_Year"]==1].index[0]
runner_up = nhl_info[nhl_info["Last_Year"]==2].index[0]
semi_finalists = list(nhl_info[nhl_info["Last_Year"]==3].index)
random.shuffle(semi_finalists)
semi_finalist1 = semi_finalists[0]; semi_finalist2 = semi_finalists[1]
if cant_host_df.loc[cup_winner,"2022-10-11"] == 0:
    home_team = cup_winner
elif cant_host_df.loc[runner_up,"2022-10-11"] == 0:
    home_team = runner_up
elif cant_host_df.loc[semi_finalist1,"2022-10-11"] == 0:
    home_team = semi_finalist1
elif cant_host_df.loc[semi_finalist2,"2022-10-11"] == 0:
    home_team = semi_finalist2
else: print("what's the deal with all these scheduling conflicts?\
\n make program accounting for quarter-finalists..."); sys.exit(0)

print("I will now make the schedule for the 2022-2023 season.")
print("This may take up to 5 minutes. Please stand by...")

# no exclusions necessary as this is the first game (only exception is home arena unavailability
# which was handled above. In actual 2022-2023 season, 2021-2022 cup winner couldn't host because of a concert)
away_team = random.choice(nhl_info[(nhl_info["Div"] == nhl_info.loc[home_team,"Div"]) & (nhl_info.index != home_team)].index)
game1 = away_team+"-"+home_team
season_games_list.append(game1)
games_played_list.remove(game1)
today_list.append(away_team); today_list.append(home_team)
games_by_date[current_date] = [game1]

away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()
nhl_dynamic = dynamic_updates(df = nhl_dynamic)
tomorrow_priority_list = non_prio_consequences(tomorrow_priority_list = tomorrow_priority_list)

# second game on opening night is hosted on west coast for TV-friendly doubleheader.
# Cali has large media markets
while True:
    home_team2 = random.choice(nhl_info[nhl_info["State"] == "CA"].index)
    away_team2 = random.choice(nhl_info[(nhl_info["Div"] == nhl_info.loc[home_team2,"Div"]) & (nhl_info.index != home_team2)].index)
    game2 = away_team2+"-"+home_team2
    if game2 != game1: break
    else: continue # not possi

season_games_list.append(game2)
games_played_list.remove(game2)
games_by_date[current_date].append(game2) # no need to check if dict key exists as on later days
today_list.append(away_team2); today_list.append(home_team2)

away_team = away_team2
home_team = home_team2
away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()
nhl_dynamic = dynamic_updates(df = nhl_dynamic)

tomorrow_priority_list = non_prio_consequences(tomorrow_priority_list = tomorrow_priority_list)

# EOD for day 1
for team in nhl_info.index:
    if (team not in today_list) & (nhl_dynamic.loc[team,"games_played"] > 0):
        nhl_dynamic.loc[team,"rest_days"] += 1
current_date = (pd.to_datetime(current_date) + pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")
today_list.clear()

if tomorrow_priority_list:
    for game in tomorrow_priority_list:
        if game not in games_played_list:
            tomorrow_priority_list.remove(game)
    priority_list += tomorrow_priority_list
    tomorrow_priority_list.clear()

### ***** PART 3B1 ***** ####
### MAIN SCHEDULING BODY UNTIL WEEK BEFORE ALL-STAR BREAK ###
schedule_runs = 0
while True: # outer loop restarts schedule if a bad run makes it go more than one week longer than actual 2022-2023 schedule.
    while current_date < "2023-01-24":
        max_games = determine_max_games(games_by_day_presb,pd.to_datetime(current_date).strftime("%A"))
        if max_games < 14: max_games += 3 # correcting for original (arbitrary) being too low
        elif 13 < max_games < 16: max_games += 1
        if current_date in holidays:
            current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
            end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
            continue # next day

        daily_list = games_played_list[:]
        today_list.clear()
        max_gp_teams = []; min_gp_teams = []
        min_prio_teams = []; min_no_prio = []

        # the priority list "forces" certain games to be played. This is what allows
        # teams to play games in a cluster as a means of reducing travel
        if priority_list:
            priority_list = [game for game in priority_list if game in games_played_list]

        # this block makes it so that all teams are close to each other in games played as in the actual NHL schedule
        # if left random there will be big differences
        if (max(nhl_dynamic["games_played"]) - min(nhl_dynamic["games_played"])) >= 4: # make 3 or 5 instead of 4?
            nhl_dyn_sort = nhl_dynamic.sort_values(["games_played","rest_days"], ascending = [True,False])
            min_gp_teams = list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == min(nhl_dyn_sort["games_played"])].index) # order min teams by longest rest - loop through them in this order
            max_gp_teams = list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == max(nhl_dyn_sort["games_played"])].index)
            if priority_list: # split teams with minimum games played (GP) into those with games on priority list and those not
                for team in min_gp_teams:
                    min_gp_str = re.compile(team)
                    if any(filter(min_gp_str.search,priority_list)):
                        min_prio_teams.append(team)
                    else: min_no_prio.append(team)
            else: min_no_prio = min_gp_teams[:]

        # don't want teams with highest games played to play, but is necessary if
        # they're on priority list so those games can be cleared
        for max_gp_team in max_gp_teams:
            team_str = re.compile(max_gp_team)
            max_prio = [game for game in priority_list if re.search(team_str,game)]
            daily_list = [game for game in daily_list if not re.search(team_str,game)]
            daily_list += max_prio

        if min_prio_teams:
            for min_prio_team in min_prio_teams: # try to schedule games from priority list first
                if (not daily_list) | (not priority_list):
                    break # will skip down to next for loop. Will check for same condition again and then send to EOD in next while loop
                if current_date in games_by_date.keys():
                    if len(games_by_date[current_date]) == max_games: break
                min_prio_str = re.compile(min_prio_team)
                min_prio_home_str = re.compile("-"+min_prio_team) # home teams are after the dash in AWY-HME format; away teams come before
                min_prio_games = [game for game in priority_list if re.search(min_prio_str,game)] # list of all of chosen min team's games
                if not min_prio_games:
                    continue

                # SCENARIO 1 -  Loop through min_prio games and try to schedule one.
                # Break for loop if game is scheduled or team can't play and move on to next min_prio team
                for game in min_prio_games:
                    game_to_check = game
                    away_team,home_team = get_teams_from_game(game_to_check)
                    away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                    mpg_string = mpg_exclusions()
                    if mpg_string == "break":
                        # if a priority list game can't be played, it's moved to tomorrow priority list
                        # which ensures that priority games are cleared as quickly as possible and maintain priority status
                        priority_list.remove(game_to_check); tomorrow_priority_list.append(game_to_check)
                        if game_to_check in daily_list: daily_list.remove(game_to_check) # safety check
                        break
                    if mpg_string == "continue":
                        priority_list.remove(game_to_check); tomorrow_priority_list.append(game_to_check)
                        if game_to_check in daily_list: daily_list.remove(game_to_check)
                        continue

                       # scheduling routine 1 (see doc string)
                    season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                    scheduling_routine_mpg(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                    break # go to next team (break for loop of games for one team)
                continue # go to next team (continue in for loop through teams on prio list with min GP)

            # SCENARIO 2:
            # if a min prio team couldn't schedule one of their games from the priority list,
            # try to schedule a home non-prio game as long as their prio game is a home game
            # this boosts their GP and won't interfere with priority list
            for min_prio_team in min_prio_teams:
                if min_prio_team in today_list: # already had game scheduled on current date above
                    continue # next team
                if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
                    if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
                    (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 850): # played > 850 from home previous night
                        continue
                min_prio_home_str = re.compile("-"+min_prio_team)
                if (any(filter(min_prio_home_str.search,priority_list))) & (check_all_intervals(min_prio_team) == True) & \
                (cant_host_df.loc[min_prio_team,current_date] != 1): # makes sure team can play at home on current date
                    mp_home_games = [game for game in daily_list if re.search(min_prio_home_str,game)]
                    mp_home_games = [game for game in mp_home_games if (game not in priority_list) & (game not in tomorrow_priority_list)]

                    for game in mp_home_games:
                        away_team,home_team = get_teams_from_game(game)
                        away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                        mnp_string = min_noprio_exclusions()

                        if mnp_string == "remove_home_abbrv": # increase speed by removing as many games as possible from daily list when applicable
                            daily_list.remove(game_to_check)
                            break # advance to next team
                        if mnp_string == "remove_home_str":
                            daily_list.remove(game_to_check)
                            break
                        if mnp_string == "remove_away_abbrv":
                            daily_list.remove(game_to_check)
                            continue # next game for this team
                        if mnp_string == "remove_away_str":
                            daily_list.remove(game_to_check)
                            continue
                        if mnp_string == "mnp_remove":
                            daily_list.remove(game_to_check)
                            continue

                        # scheduling routine 2
                        season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                        scheduling_routine_npc(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                        break # break for loop of games to go to next team
                    continue # continue for loop of min prio teams to go to next team

        for min_np_team in min_no_prio: # schedule games for teams on min GP list but who don't have priority games
            if not daily_list:
                break # will skip down to next for loop. Will check for same condition again and then send to EOD in next while loop
            min_np_str = re.compile(min_np_team)
            if current_date in games_by_date.keys():
                if len(games_by_date[current_date]) == max_games: break
                if any(filter(min_np_str.search,games_by_date[current_date])):
                    continue # team already has game scheduled today. Loop through them
            min_np_games = [game for game in daily_list if re.search(min_np_str,game)] # all games on daily list for no prio min GP team

            while True: # SCENARIO 3 - looking through min no priority games for one team. Just looking for any game for min_gp team
                if (not daily_list) | (not min_np_games): break
                if not any(filter(min_np_str.search,daily_list)): break # current team has exhausted all available games. Will advance to next team
                game_to_check = random.choice(min_np_games)
                away_team,home_team = get_teams_from_game(game_to_check)
                away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                        # this version doesn't limit road trips and homestands to 8. Will add in if necessary
                mnp_string = min_noprio_exclusions()

                if mnp_string == "remove_home_abbrv":
                    min_np_games = [game for game in min_np_games if not re.search(home_abbrv_str,game)] # can manipulate this list directly because not using for loop
                    daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                    if home_team == min_np_team: break # advance to next team - same below
                    else: continue # next game for this team - same below
                if mnp_string == "remove_home_str":
                    min_np_games = [game for game in min_np_games if not re.search(home_str,game)]
                    daily_list = [game for game in daily_list if not re.search(home_str,game)]
                    continue
                if mnp_string == "remove_away_abbrv":
                    min_np_games = [game for game in min_np_games if not re.search(away_abbrv_str,game)]
                    daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                    if away_team == min_np_team: break
                    else: continue
                if mnp_string == "remove_away_str":
                    min_np_games = [game for game in min_np_games if not re.search(away_str,game)]
                    daily_list = [game for game in daily_list if not re.search(away_str,game)]
                    continue
                if mnp_string == "mnp_remove":
                    min_np_games.remove(game_to_check); daily_list.remove(game_to_check)
                    continue
                       # scheduling routine 3
                season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                scheduling_routine_npc(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                break # go to next team
            continue # go to next team
        # done with min GP routine

        while True:
            if (max_games == 0) | (not daily_list): # EOD
                current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                break

            if current_date in games_by_date.keys():
                if len(games_by_date[current_date]) == max_games:
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break

            if priority_list: # SCENARIO 4: There is priority list.
                priority_list = [game for game in priority_list if game in games_played_list] # safety check
                for game_to_check in priority_list: # allows oldest to be dealt with first although for loop isn't ideal
                    away_team,home_team = get_teams_from_game(game_to_check)
                    away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                    if priority_list_exclusions() == "pl remove":
                        continue
                    if game_to_check not in daily_list: continue

                   # scheduling routine 4
                    season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                    scheduling_routine_prio(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                    if len(games_by_date[current_date]) == max_games: # EOD
                        current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                        end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                        break
                    else: continue
                # any games from priority list that weren't scheduled are added to tomorrow priority list
                priority_list = [game for game in priority_list if game not in season_games_list]
                tomorrow_priority_list += priority_list
                priority_list.clear()

            else: # SCENARIO 5: No priority list
                if current_date in games_by_date.keys():
                    if len(games_by_date[current_date]) == max_games: #EOD
                        current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                        end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                        break
                game_to_check = random.choice(daily_list)
                away_team,home_team = get_teams_from_game(game_to_check)
                away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                npe_string = non_prio_exclusions()

                if npe_string == "remove_home_abbrv":
                    daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                    continue
                if npe_string == "remove_home_str":
                    daily_list = [game for game in daily_list if not re.search(home_str,game)]
                    continue
                if npe_string == "remove_away_abbrv":
                    daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                    continue
                if npe_string == "remove_away_str":
                    daily_list = [game for game in daily_list if not re.search(away_str,game)]
                    continue
                if npe_string == "exclusions_list":
                    daily_list.remove(game_to_check)
                    continue

                # scheduling routine 5 - didn't functionize this version because it's short and doesn't appear often
                season_games_list.append(game_to_check); games_played_list.remove(game_to_check)
                daily_list.remove(game_to_check)
                if current_date not in games_by_date.keys():
                    games_by_date[current_date] = [game_to_check]
                else: games_by_date[current_date].append(game_to_check)
                today_list.append(away_team); today_list.append(home_team)

                nhl_dynamic = dynamic_updates(df = nhl_dynamic)
                tomorrow_priority_list = non_prio_consequences(tomorrow_priority_list = tomorrow_priority_list)

                daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                if len(games_by_date[current_date]) == max_games: # EOD
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break
                #continue
    before_asg = [] # makes list of teams who play before all star game (ASG)
    # and therefore have bye week after all star break (ASB)
    print("Season scheduled through all-star break...")

    ### ***** PART 3B2 ***** ####
    ### MAIN SCHEDULING BODY UNTIL WEEK AFTER ALL-STAR BREAK ###
    while current_date < "2023-02-10":
        max_games = determine_max_games(games_by_day_presb,pd.to_datetime(current_date).strftime("%A"))
        if "2023-01-30" < current_date < "2023-02-03":
            max_games = 5
        if current_date == "2023-02-05": # reset all road trips and homestands after ASB
            for team in nhl_info.index:
                nhl_dynamic.loc[team,"homestand"] = 0; nhl_dynamic.loc[team,"road_trip"] = 0
                nhl_dynamic.loc[team,"rest_days"] = 0; nhl_dynamic.loc[team,"location"] = team
                nhl_dynamic.loc[team,"long_road_trip"] = 0; nhl_dynamic.loc[team,"rt_first"] = team
            priority_list.clear(); tomorrow_priority_list.clear() # safety check
        if current_date in holidays:
            current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
            end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
            continue # next day


        daily_list = games_played_list[:]
        today_list.clear()
        max_gp_teams = []; min_gp_teams = []
        min_prio_teams = []; min_no_prio = []

        # priority list comes before min GP routine in lead up to ASG. All prio games
        # must be clear by the ASG so that a road trip in a cluster isn't split before and after ASG
        if priority_list: # SCENARIO 6: There is priority list (between 2023-01-24 and 2023-02-10)
            priority_list = [game for game in priority_list if game in games_played_list]
            for game_to_check in priority_list:
                away_team,home_team = get_teams_from_game(game_to_check)
                away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                if priority_list_exclusions() == "pl remove":
                    continue
                if game_to_check not in daily_list: continue

                   # scheduling routine 6 - not functionized because of special all-star related updates
                season_games_list.append(game_to_check);
                games_played_list.remove(game_to_check)
                if current_date not in games_by_date.keys():
                    games_by_date[current_date] = [game_to_check]
                else: games_by_date[current_date].append(game_to_check)
                if game_to_check in tomorrow_priority_list: tomorrow_priority_list.remove(game_to_check)
                daily_list.remove(game_to_check)
                today_list.append(away_team); today_list.append(home_team)
                if current_date < "2023-02-02":
                    before_asg.append(home_team); before_asg.append(away_team)

                nhl_dynamic = dynamic_updates(df = nhl_dynamic)

                daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]

                if len(games_by_date[current_date]) == max_games: # EOD
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break
                else: continue
            tomorrow_priority_list += priority_list
            priority_list.clear()

        if (max(nhl_dynamic["games_played"]) - min(nhl_dynamic["games_played"])) >= 4: # make 3 or 5 instead of 4?
            nhl_dyn_sort = nhl_dynamic.sort_values(["games_played","rest_days"], ascending = [True,False])
            min_gp_teams =  list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == min(nhl_dyn_sort["games_played"])].index) # order min teams by longest rest - loop through them in this order
            max_gp_teams = list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == max(nhl_dyn_sort["games_played"])].index)
            min_no_prio = min_gp_teams[:]

            for max_gp_team in max_gp_teams:
                team_str = re.compile(max_gp_team)
                max_prio = [game for game in priority_list if re.search(team_str,game)]
                daily_list = [game for game in daily_list if not re.search(team_str,game)]
                daily_list += max_prio

            for min_np_team in min_no_prio: # schedule games for teams on min GP list but who don't have priority games
                if not daily_list:
                    break # will skip down to next (while) loop. Will check for same condition again and then send to EOD in next while loop
                min_np_str = re.compile(min_np_team)
                if current_date in games_by_date.keys():
                    if len(games_by_date[current_date]) == max_games: break # go down to next loop (while)
                    if any(filter(min_np_str.search,games_by_date[current_date])):
                        continue # team already has game scheduled today. Loop through them
                min_np_games = [game for game in daily_list if re.search(min_np_str,game)] # all games on daily list for no prio min GP team

                while True: # SCENARIO 7 - looking through min no priority games for one team. Just looking for any game for min_gp team
                # (between 2023-01-24 and 2023-02-10)
                    if (not daily_list) | (not min_np_games): break
                    if not any(filter(min_np_str.search,daily_list)): break # current team has exhausted all available games. Will advance to next team
                    game_to_check = random.choice(min_np_games)
                    away_team,home_team = get_teams_from_game(game_to_check)
                    away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                    mnp_string = min_noprio_exclusions()

                    if mnp_string == "remove_home_abbrv":
                        min_np_games = [game for game in min_np_games if not re.search(home_abbrv_str,game)]
                        daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                        if home_team == min_np_team: break # advance to next team
                        else: continue # next game for this team - same below
                    if mnp_string == "remove_home_str":
                        min_np_games = [game for game in min_np_games if not re.search(home_str,game)]
                        daily_list = [game for game in daily_list if not re.search(home_str,game)]
                        continue
                    if mnp_string == "remove_away_abbrv":
                        min_np_games = [game for game in min_np_games if not re.search(away_abbrv_str,game)]
                        daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                        if away_team == min_np_team: break
                        else: continue
                    if mnp_string == "remove_away_str":
                        min_np_games = [game for game in min_np_games if not re.search(away_str,game)]
                        daily_list = [game for game in daily_list if not re.search(away_str,game)]
                        continue
                    if mnp_string == "mnp_remove":
                        min_np_games.remove(game_to_check); daily_list.remove(game_to_check)
                        continue

                    # DON'T TRIGGER PRIORITY GAMES BEFORE ASG #
                    if "2023-01-24" < current_date < "2023-02-03":
                        if allstar_triggers() == "daily remove":
                            min_np_games.remove(game_to_check)
                            if game_to_check in daily_list: daily_list.remove(game_to_check)
                            continue

                    if "2023-02-05" < current_date < "2023-02-09":
                        if (away_team in before_asg) | (home_team in before_asg):
                            # team that played in week before the ASB gets bye after ASB
                            min_np_games.remove(game_to_check)
                            if game_to_check in daily_list:
                                daily_list.remove(game_to_check);
                            continue

                    # scheduling routine 7
                    season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                    scheduling_routine_npc(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                    break # go to next team in min no prio (advance for loop)
                continue # go to next team or go to next loop if out of teams

        while True:
            if (max_games == 0) | (not daily_list): # EOD
                current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                break

            if current_date in games_by_date.keys():
                if len(games_by_date[current_date]) == max_games: # EOD
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break

            game_to_check = random.choice(daily_list)
            away_team,home_team = get_teams_from_game(game_to_check)
            away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

            #SCENARIO 8 - non priority games (between 2023-01-24 and 2023-02-10)
            npe_string = non_prio_exclusions()

            if npe_string == "remove_home_abbrv":
                daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                continue
            if npe_string == "remove_home_str":
                daily_list = [game for game in daily_list if not re.search(home_str,game)]
                continue
            if npe_string == "remove_away_abbrv":
                daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                continue
            if npe_string == "remove_away_str":
                daily_list = [game for game in daily_list if not re.search(away_str,game)]
                continue
            if npe_string == "exclusions_list":
                daily_list.remove(game_to_check)
                continue

            #DON'T TRIGGER PRIORITY GAMES BEFORE ASG #
            if "2023-01-24" < current_date < "2023-02-03":
                if allstar_triggers() == "daily remove":
                    daily_list.remove(game_to_check)
                    continue

            if "2023-02-05" < current_date < "2023-02-09":
                if (away_team in before_asg) | (home_team in before_asg):
                    daily_list.remove(game_to_check)
                    continue

                # cases below check for availability of certain matchups including ASB bye status
                if (away_team in ["EDM","CAL"]) & (home_team in ["LAK","ANA"]):
                    if long_div_after_asb(["EDM","CAL"],["LAK","ANA"]) == "daily remove":
                        daily_list.remove(game_to_check)
                        continue
                if (away_team in ["LAK","ANA"]) & (home_team in ["EDM","CAL"]):
                    if long_div_after_asb(["LAK","ANA"],["EDM","CAL"]) == "daily remove":
                        daily_list.remove(game_to_check)
                        continue
                if (away_team in ["MON","OTT"]) & (home_team in ["FLA","TBL"]):
                    if long_div_after_asb(["MON","OTT"],["FLA","TBL"]) == "daily remove":
                        daily_list.remove(game_to_check)
                        continue
                if (away_team in ["FLA","TBL"]) & (home_team in ["MON","OTT"]):
                    if long_div_after_asb(["FLA","TBL"],["MON","OTT"]) == "daily remove":
                        daily_list.remove(game_to_check)
                        continue

                if (away_team == "DAL") & (home_team in north_east):
                    northeast_others = north_east[:]
                    northeast_others.remove(home_team)
                    temp_clust_list = []
                    for team in northeast_others:
                        if ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7) & \
                        (away_team+"-"+home_team not in priority_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
                            temp_clust_list.append(True)
                            break
                        clust_away_str = re.compile(team+"-")
                        temp_clust_list.append(any(filter(clust_away_str.search,tomorrow_priority_list)))
                        temp_clust_list.append(any(filter(clust_away_str.search,priority_list)))
                        if team in before_asg:
                            temp_clust_list.append(True)
                            break
                    if any(temp_clust_list):
                        daily_list.remove(game_to_check)
                        temp_clust_list.clear()
                        continue

                if (away_team in pac_plus) & (home_team in east_plus): # don't schedule pac_plus @ east_plus if there aren't at least 2 more east_plus teams available to be added to prio list
                    pac_plus_away_str = re.compile(away_team+"-")
                    if (not any(filter(pac_plus_away_str.search,tomorrow_priority_list))) & \
                    (nhl_dynamic.loc[away_team,"location"] in east_plus):
                        daily_list.remove(game_to_check)
                        continue # don't make them do another round of east_plus if just finished one
                    if home_team in clusters_list:
                        home_clustermates = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                        home_clustermates.remove(home_team)
                        temp_clust_list = []
                        for team in home_clustermates:
                            if ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7) & \
                            (nhl_dynamic.loc[team,"location"] not in clusters_list) & \
                            (away_team+"-"+home_team not in priority_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
                                temp_clust_list.append(True)
                                break
                            clust_away_str = re.compile(team+"-")
                            temp_clust_list.append(any(filter(clust_away_str.search,tomorrow_priority_list)))
                            temp_clust_list.append(any(filter(clust_away_str.search,priority_list)))
                            if team in before_asg:
                                temp_clust_list.append(True)
                                break
                        home_clustermates.append(home_team)
                        if any(temp_clust_list):
                            daily_list.remove(game_to_check)
                            temp_clust_list.clear()
                            continue
                    east_plus_avail = []
                    east_check = east_plus[:]
                    east_check.remove(home_team)
                    for team in east_check:
                        team_str = re.compile(team+"-")
                        if (any(filter(team_str.search,priority_list))) | (any(filter(team_str.search,tomorrow_priority_list))) | \
                        (nhl_dynamic.loc[team,"homestand"] > 9) | (team in before_asg) | \
                        ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7):
                            home_str = re.compile("-"+team)
                            daily_list = [game for game in daily_list if not re.search(home_str,game)]
                        else:
                            east_plus_avail.append(team)

                    if len(east_plus_avail) < 2:
                        daily_list.remove(game_to_check)
                        continue

                if 1000 < measure_distance(away_team,home_team) < 1396: # don't trigger new round of priority if has just finished one
                    if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
                        cen_west_str = re.compile(away_team+"-")
                        if (not any(filter(cen_west_str.search,tomorrow_priority_list))) & \
                        (nhl_dynamic.loc[away_team,"location"] in list(nhl_info[nhl_info["Conf"] == "E"].index)):
                            daily_list.remove(game_to_check)
                            continue

                        if home_team in clusters_list:
                            home_clustermates = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                            home_clustermates.remove(home_team)
                            temp_clust_list = []
                            for team in home_clustermates:
                                if ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7) & \
                                (nhl_dynamic.loc[team,"location"] not in clusters_list) & \
                                (away_team+"-"+home_team not in priority_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
                                    temp_clust_list.append(True)
                                    break
                                clust_away_str = re.compile(team+"-")
                                temp_clust_list.append(any(filter(clust_away_str.search,tomorrow_priority_list)))
                                temp_clust_list.append(any(filter(clust_away_str.search,priority_list)))
                                if team in before_asg:
                                    temp_clust_list.append(True)
                            home_clustermates.append(home_team)
                            if any(temp_clust_list):
                                daily_list.remove(game_to_check)
                                temp_clust_list.clear()
                                continue

                if (away_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & (home_team == "COL"):
                    temp_sw_list = []
                    for team in ["VGK","ARI"]:
                        if ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7) & \
                        (nhl_dynamic.loc[team,"location"] not in clusters_list) & \
                        (away_team+"-"+home_team not in priority_list) | (away_team+"-"+home_team not in tomorrow_priority_list) & \
                        (nhl_dynamic.loc[team,"home_games"] < 41):
                            temp_sw_list.append(True)
                            break
                        if team in before_asg:
                            temp_sw_list.append(True)
                            break
                        sw_away_str = re.compile("-"+team)
                        temp_sw_list.append(any(filter(sw_away_str.search,tomorrow_priority_list)))
                        temp_sw_list.append(any(filter(sw_away_str.search,priority_list)))
                    if any(temp_sw_list):
                        daily_list.remove(game_to_check)
                        temp_sw_list.clear()
                        continue
                    if (any(filter(opposite_away_str.search,tomorrow_priority_list))) | (any(filter(opposite_away_str.search,priority_list))):
                        continue

                if (measure_distance(away_team,home_team) > 1396) & (not (away_team in pac_plus) & (home_team in east_plus)): # don't schedule game if this will trigger priority games for home team's clustermates and they're on tpl as away team
                    if home_team in clusters_list:
                        home_clustermates = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                        home_clustermates.remove(home_team)
                        temp_clust_list = []
                        for team in home_clustermates:
                            if ((nhl_dynamic.loc[team,"home_games"] - nhl_dynamic.loc[team,"away_games"]) > 7) & \
                            (nhl_dynamic.loc[team,"location"] not in clusters_list) & \
                            (away_team+"-"+home_team not in priority_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
                                temp_clust_list.append(True)
                                break
                            if team in before_asg:
                                temp_clust_list.append(True)
                                break
                            clust_away_str = re.compile(team+"-")
                            temp_clust_list.append(any(filter(clust_away_str.search,tomorrow_priority_list)))
                            temp_clust_list.append(any(filter(clust_away_str.search,priority_list)))
                        home_clustermates.append(home_team)
                        if any(temp_clust_list):
                            daily_list.remove(game_to_check)
                            temp_clust_list.clear()
                            continue

            # scheduling routine 8
            season_games_list.append(game_to_check)
            games_played_list.remove(game_to_check)
            daily_list.remove(game_to_check)
            if current_date not in games_by_date.keys():
                games_by_date[current_date] = [game_to_check]
            else: games_by_date[current_date].append(game_to_check)
            today_list.append(away_team); today_list.append(home_team)
            if "2023-01-29" < current_date < "2023-02-02":
                before_asg.append(home_team); before_asg.append(away_team)

            nhl_dynamic = dynamic_updates(df = nhl_dynamic)
            tomorrow_priority_list = non_prio_consequences(tomorrow_priority_list = tomorrow_priority_list)

            daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
            daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
            if len(games_by_date[current_date]) == max_games: # EOD
                current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                break
    print("Season scheduled through March 29...")
    ### ***** PART 3B3 ***** ####
    ### MAIN SCHEDULING BODY FROM AFTER ASB UNTIL END OF MARCH ###
    while current_date < "2023-03-29": # chose this date after trial and error
        max_games = determine_max_games(games_by_day_postsb,pd.to_datetime(current_date).strftime("%A"))
        if max_games < 14: max_games += 3
        elif 13 < max_games < 16: max_games += 1
        if current_date == super_bowl: max_games = 3
        if current_date in holidays:
            current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
            end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
            continue # next day

        daily_list = games_played_list[:]
        today_list.clear()
        max_gp_teams = []; min_gp_teams = []
        min_prio_teams = []; min_no_prio = []

        if priority_list:
            priority_list = [game for game in priority_list if game in games_played_list]

        if (max(nhl_dynamic["games_played"]) - min(nhl_dynamic["games_played"])) >= 4:
            nhl_dyn_sort = nhl_dynamic.sort_values(["games_played","rest_days"], ascending = [True,False])
            min_gp_teams =  list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == min(nhl_dyn_sort["games_played"])].index) # order min teams by longest rest - loop through them in this order
            max_gp_teams = list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == max(nhl_dyn_sort["games_played"])].index)
            if priority_list:
                for team in min_gp_teams:
                    min_gp_str = re.compile(team)
                    if any(filter(min_gp_str.search,priority_list)):
                        min_prio_teams.append(team)
                    else: min_no_prio.append(team)
            else: min_no_prio = min_gp_teams[:]

        for max_gp_team in max_gp_teams:
            team_str = re.compile(max_gp_team)
            max_prio = [game for game in priority_list if re.search(team_str,game)]
            daily_list = [game for game in daily_list if not re.search(team_str,game)]
            daily_list += max_prio
            for min_gp_team in min_gp_teams: # added for end of season to make less restrictive and prevent min GP teams from being stuck with no opponents
                if (min_gp_team+"-"+max_gp_team) in games_played_list:
                    daily_list.append(min_gp_team+"-"+max_gp_team)
                if (max_gp_team+"-"+min_gp_team) in games_played_list:
                    daily_list.append(max_gp_team+"-"+min_gp_team)

        if min_prio_teams:
            for min_prio_team in min_prio_teams: # try to schedule games from priority list first
                if (not daily_list) | (not priority_list):
                    break # will skip down to next for loop. Will check for same condition again and then send to EOD in next while loop
                if current_date in games_by_date.keys():
                    if len(games_by_date[current_date]) == max_games: break
                min_prio_str = re.compile(min_prio_team)
                min_prio_games = [game for game in priority_list if re.search(min_prio_str,game)]
                # list of all of chosen min team's games
                if not min_prio_games:
                    continue

                # SCENARIO 9 -  Loop through min_prio games and see what can be scheduled.
                #Break this loop if game is scheduled and move on to next min_prio team. (between 2023-02-10 and 2023-03-29)

                for game in min_prio_games:
                    game_to_check = game
                    away_team,home_team = get_teams_from_game(game_to_check)
                    away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                    mpg_string = mpg_exclusions()

                    if mpg_string == "break":
                        priority_list.remove(game_to_check); tomorrow_priority_list.append(game_to_check)
                        if game_to_check in daily_list: daily_list.remove(game_to_check)
                        break
                    if mpg_string == "continue":
                        priority_list.remove(game_to_check); tomorrow_priority_list.append(game_to_check)
                        if game_to_check in daily_list: daily_list.remove(game_to_check)
                        continue

                   # scheduling routine 9
                    season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                    scheduling_routine_mpg(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                    break # go to next team
                continue # go to next team

            for min_prio_team in min_prio_teams:
                if min_prio_team in today_list:
                    continue # next team
                if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
                    if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
                    (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 850):
                        continue
                min_prio_home_str = re.compile("-"+min_prio_team)
                if (any(filter(min_prio_home_str.search,priority_list))) & (check_all_intervals(min_prio_team) == True) & \
                (cant_host_df.loc[min_prio_team,current_date] != 1):
                    mp_home_games = [game for game in daily_list if re.search(min_prio_home_str,game)]
                    mp_home_games = [game for game in mp_home_games if (game not in priority_list) & (game not in tomorrow_priority_list)]

                    # SCENARIO 10 - Home non-priority games for team with min GP (between 2023-02-10 and 2023-03-29)
                    for game in mp_home_games:
                        away_team,home_team = get_teams_from_game(game)
                        away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                        mnp_string = min_noprio_exclusions()

                        if mnp_string == "remove_home_abbrv":
                            daily_list.remove(game_to_check)
                            break # advance to next team
                        if mnp_string == "remove_home_str":
                            daily_list.remove(game_to_check)
                            break
                        if mnp_string == "remove_away_abbrv":
                            daily_list.remove(game_to_check)
                            continue # next game for this team
                        if mnp_string == "remove_away_str":
                            daily_list.remove(game_to_check)
                            continue
                        if mnp_string == "mnp_remove":
                            daily_list.remove(game_to_check)
                            continue

                        # scheduling routine 10
                        season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                        scheduling_routine_npc(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                        break # break go to next team
                    continue # go to next team

        for min_np_team in min_no_prio: # schedule games for teams on min GP list but who don't have priority games
            if not daily_list:
                break # will skip down to next for loop. Will check for same condition again and then send to EOD in next while loop
            min_np_str = re.compile(min_np_team)
            if current_date in games_by_date.keys():
                if len(games_by_date[current_date]) == max_games: break
                if any(filter(min_np_str.search,games_by_date[current_date])):
                    continue # team already has game scheduled today. Loop through them
            min_np_games = [game for game in daily_list if re.search(min_np_str,game)] # all games on daily list for no prio min GP team

            while True: # SCENARIO 11 - looking through min no priority games for one team. Just looking for any game for min_gp team
            # (between 2023-02-10 and 2023-03-29)
                if (not daily_list) | (not min_np_games): break
                if not any(filter(min_np_str.search,daily_list)): break # current team has exhausted all available games. Will advance to next team
                game_to_check = random.choice(min_np_games)
                away_team,home_team = get_teams_from_game(game_to_check)
                away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                mnp_string = min_noprio_exclusions()

                if mnp_string == "remove_home_abbrv":
                    min_np_games = [game for game in min_np_games if not re.search(home_abbrv_str,game)]
                    daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                    if home_team == min_np_team: break # advance to next team b/c team can't play on current date
                    else: continue # next game for this team
                if mnp_string == "remove_home_str":
                    min_np_games = [game for game in min_np_games if not re.search(home_str,game)]
                    daily_list = [game for game in daily_list if not re.search(home_str,game)]
                    continue
                if mnp_string == "remove_away_abbrv":
                    min_np_games = [game for game in min_np_games if not re.search(away_abbrv_str,game)]
                    daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                    if away_team == min_np_team: break # advance to next team b/c team can't play on current date
                    else: continue
                if mnp_string == "remove_away_str":
                    min_np_games = [game for game in min_np_games if not re.search(away_str,game)]
                    daily_list = [game for game in daily_list if not re.search(away_str,game)]
                    continue
                if mnp_string == "mnp_remove":
                    min_np_games.remove(game_to_check); daily_list.remove(game_to_check)
                    continue

                       # scheduling routine 11
                season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                scheduling_routine_npc(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                break # go to next team
            continue # go to next team

        while True:
            if (max_games == 0) | (not daily_list): # EOD
                current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                break

            if current_date in games_by_date.keys():
                if len(games_by_date[current_date]) == max_games:
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break

            if priority_list: # SCENARIO 12: There is priority list (after min GP routines). (Between 2023-02-10 and 2023-03-29)
                priority_list = [game for game in priority_list if game in games_played_list]
                for game_to_check in priority_list: # allows oldest to be dealt with first
                    away_team,home_team = get_teams_from_game(game_to_check)
                    away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                    if priority_list_exclusions() == "pl remove":
                        continue
                    if game_to_check not in daily_list: continue

                   # scheduling routine 12
                    season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                    scheduling_routine_prio(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                    if len(games_by_date[current_date]) == max_games: # EOD
                        current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                        end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                        break
                    else: continue
                priority_list = [game for game in priority_list if game not in season_games_list]
                tomorrow_priority_list += priority_list
                priority_list.clear()

            else: # SCENARIO 13: No priority list (between 2023-02-10 and 2023-03-29)
                if current_date in games_by_date.keys():
                    if len(games_by_date[current_date]) == max_games:
                        current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                        end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                        break
                game_to_check = random.choice(daily_list)
                away_team,home_team = get_teams_from_game(game_to_check)
                away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                npe_string = non_prio_exclusions()

                if npe_string == "remove_home_abbrv":
                    daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                    continue
                if npe_string == "remove_home_str":
                    daily_list = [game for game in daily_list if not re.search(home_str,game)]
                    continue
                if npe_string == "remove_away_abbrv":
                    daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                    continue
                if npe_string == "remove_away_str":
                    daily_list = [game for game in daily_list if not re.search(away_str,game)]
                    continue
                if npe_string == "exclusions_list":
                    daily_list.remove(game_to_check)
                    continue

                # scheduling routine 13
                season_games_list.append(game_to_check)
                games_played_list.remove(game_to_check)
                daily_list.remove(game_to_check)
                if current_date not in games_by_date.keys():
                    games_by_date[current_date] = [game_to_check]
                else: games_by_date[current_date].append(game_to_check)
                today_list.append(away_team); today_list.append(home_team)

                nhl_dynamic = dynamic_updates(df = nhl_dynamic)
                tomorrow_priority_list = non_prio_consequences(tomorrow_priority_list = tomorrow_priority_list)

                daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                if len(games_by_date[current_date]) == max_games: # EOD
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break

    print("Almost done!!")
    ### ***** PART 3B4 ***** ####
    ### SCHEDULING FOR END OF SEASON ###
    while games_played_list:
        if current_date == "2023-05-01": # cuts off program if bad run from unlikely randomization
            break
        max_games = determine_max_games(games_by_day_postsb,pd.to_datetime(current_date).strftime("%A"))
        if max_games < 13: max_games += 4
        elif 12 < max_games < 16: max_games += 1 # to get end finished up quicker
        if current_date == "2023-04-10": max_games == 10 # based on actual 2022-2023 schedule. Mondays are usually light
        if current_date in holidays:
            current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
            end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
            continue # next day

        daily_list = games_played_list[:]
        today_list.clear()
        max_gp_teams = []; min_gp_teams = []
        min_prio_teams = []; min_no_prio = []

        if priority_list:
            priority_list = [game for game in priority_list if game in games_played_list]

        if (max(nhl_dynamic["games_played"]) - min(nhl_dynamic["games_played"])) >= 3: # tighten up a bit for end of season -
          #try to get teams to end as close to each other as possible
            nhl_dyn_sort = nhl_dynamic.sort_values(["games_played","rest_days"], ascending = [True,False])
            min_gp_teams =  list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == min(nhl_dyn_sort["games_played"])].index) # order min teams by longest rest - loop through them in this order
            max_gp_teams = list(nhl_dyn_sort[nhl_dyn_sort["games_played"] == max(nhl_dyn_sort["games_played"])].index)
            if priority_list:
                for team in min_gp_teams:
                    min_gp_str = re.compile(team)
                    if any(filter(min_gp_str.search,priority_list)):
                        min_prio_teams.append(team)
                    else: min_no_prio.append(team)
            else: min_no_prio = min_gp_teams[:]

        if max_gp_teams:
            for max_gp_team in max_gp_teams:
                team_str = re.compile(max_gp_team)
                max_prio = [game for game in priority_list if re.search(team_str,game)]
                daily_list = [game for game in daily_list if not re.search(team_str,game)]
                daily_list += max_prio
                for min_gp_team in min_gp_teams:
                    if (min_gp_team+"-"+max_gp_team) in games_played_list:
                        daily_list.append(min_gp_team+"-"+max_gp_team)
                    if (max_gp_team+"-"+min_gp_team) in games_played_list:
                        daily_list.append(max_gp_team+"-"+min_gp_team)

        if min_prio_teams:
            for min_prio_team in min_prio_teams: # try to schedule games from priority list first
                if (not daily_list) | (not priority_list):
                    break # will skip down to next for loop. Will check for same condition again and then send to EOD in next while loop
                if current_date in games_by_date.keys():
                    if len(games_by_date[current_date]) == max_games: break
                min_prio_str = re.compile(min_prio_team)
                min_prio_games = [game for game in priority_list if re.search(min_prio_str,game)]
                # list of all of chosen min team's games

                # SCENARIO 14 -  Loop through min_prio games and see what can be scheduled.
                #Break this loop if game is scheduled and move on to next min_prio team (after 2023-03-29)

                for game in min_prio_games:
                    game_to_check = game
                    away_team,home_team = get_teams_from_game(game_to_check)
                    away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                    if priority_exclusions() == "pl remove": # least restrictive exclusions. Only used here
                        priority_list.remove(game_to_check); tomorrow_priority_list.append(game_to_check)
                        if game_to_check in daily_list: daily_list.remove(game_to_check)
                        continue

                       # scheduling routine 14
                    season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                    scheduling_routine_mpg(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                    break # go to next team
                continue # go to next team

            for min_prio_team in min_prio_teams:
                if min_prio_team in today_list:
                    continue # next team
                if ((pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")) in games_by_date.keys():
                    if (any(filter(home_abbrv_str.search,games_by_date[(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%Y-%m-%d")]))) & \
                    (measure_distance(nhl_dynamic.loc[home_team,"location"],home_team) > 850):
                        continue
                min_prio_home_str = re.compile("-"+min_prio_team)
                if (any(filter(min_prio_home_str.search,priority_list))) & (check_all_intervals(min_prio_team) == True) & \
                (cant_host_df.loc[min_prio_team,current_date] != 1):
                    mp_home_games = [game for game in daily_list if re.search(min_prio_home_str,game)]
                    mp_home_games = [game for game in mp_home_games if (game not in priority_list) & (game not in tomorrow_priority_list)]

                   #SCENARIO 15 - Non prio home game for team with min GP (after 2023-03-29)
                    for game in mp_home_games:
                        away_team,home_team = get_teams_from_game(game)
                        away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                        if reduced_nonprio() == "exclusions_list": # less restrictive non priority exclusions for end of season
                           # need to get the games played at this point
                            if game in daily_list: daily_list.remove(game_to_check)
                            continue

                        # scheduling routine 15
                        season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                        scheduling_routine_npc(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                        break # go to next team
                    continue # go to next team

        for min_np_team in min_no_prio: # schedule games for teams on min GP list but who don't have priority games
            if not daily_list:
                break # will skip down to next for loop. Will check for same condition again and then send to EOD in next while loop
            min_np_str = re.compile(min_np_team)
            if current_date in games_by_date.keys():
                if len(games_by_date[current_date]) == max_games: break
                if any(filter(min_np_str.search,games_by_date[current_date])):
                    continue # team already has game scheduled today. Loop through them
            min_np_games = [game for game in daily_list if re.search(min_np_str,game)] # all games on daily list for no prio min GP team

            # SCENARIO 16 - looping through no min priority games for one team. Just looking for any game for min_gp team ( after 2023-03-29)
            for game in min_np_games:
                game_to_check = game # to re-use existing routines
                away_team,home_team = get_teams_from_game(game_to_check)
                away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                if reduced_nonprio() == "exclusions_list":
                    if game_to_check in daily_list: daily_list.remove(game_to_check)
                    continue

                 # scheduling routine 16
                season_games_list.append(game_to_check)
                games_played_list.remove(game_to_check)
                if current_date not in games_by_date.keys():
                    games_by_date[current_date] = [game_to_check]
                else: games_by_date[current_date].append(game_to_check)
                if game_to_check in tomorrow_priority_list: tomorrow_priority_list.remove(game_to_check)

                today_list.append(away_team); today_list.append(home_team)

                nhl_dynamic = dynamic_updates(df = nhl_dynamic)

                # modified consequences to get final games cleaned out
                if (away_team in pac_minus) & (home_team in north_central):
                    north_cen_other = north_central[:]
                    north_cen_other.remove(home_team)
                    north_cen_other = north_cen_other[0]
                    if (away_team+"-"+north_cen_other in games_played_list) & (away_team+"-"+north_cen_other not in tomorrow_priority_list):
                        tomorrow_priority_list.append(away_team+"-"+north_cen_other)
                    if (away_team+"-"+home_team in games_played_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
                        tomorrow_priority_list.append(away_team+"-"+home_team)

                if (away_team == "DAL") & (home_team in north_east):
                    northeast_others = north_east[:]
                    northeast_others.remove(home_team)
                    for team in northeast_others:
                        if ("DAL-"+team in games_played_list) & ("DAL-"+team not in tomorrow_priority_list):
                            tomorrow_priority_list.append("DAL-"+team)

                if (measure_distance(away_team,home_team) > 1396):
                    nhl_dynamic.loc[away_team,"long_road_trip"] = 1
                    if home_team in clusters_list:
                        home_cluster = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                        home_cluster.remove(home_team)
                        for team in home_cluster:
                            if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                                tomorrow_priority_list.append(away_team+"-"+team)
                        home_cluster.append(home_team)
                    if (away_team+"-"+home_team in games_played_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
                        tomorrow_priority_list.append(away_team+"-"+home_team)

                    if (away_team in pac_plus) & (home_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & \
                    (home_team not in clusters_list): # west coast team playing at non-cluster E conf team (excludes CHI, WIN, MIN) who is not going to be on priority list as visitor.
                        tomorrow_priority_list = pacplus_eastconf(tomorrow_priority_list = tomorrow_priority_list)

                if 1000 < measure_distance(away_team,home_team) < 1396:
                    if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
                        if home_team in clusters_list:
                            home_cluster = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                            home_cluster.remove(home_team)
                            for team in home_cluster:
                                if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                                    tomorrow_priority_list.append(away_team+"-"+team)
                            home_cluster.append(home_team)

                        else:
                            east_sample = [team for team in list(nhl_info[nhl_info["Conf"] == "E"].index) if not team in clusters_list]
                            east_sample.remove(home_team)
                            east_hold = []
                            for team in east_sample:
                                east_away = re.compile(team+"-")
                                if (any(filter(east_away.search,priority_list))) | (any(filter(east_away.search,tomorrow_priority_list))):
                                    east_hold.append(team)
                                    continue
                                if (nhl_dynamic.loc[team,"homestand"] > 9) & (nhl_dynamic.loc[team,"away_games"] < 41):
                                    east_hold.append(team)
                                    continue
                            east_sample = [team for team in east_sample if team not in east_hold]
                            east_nonclust_list = [away_team+"-"+team for team in east_sample if away_team+"-"+team in games_played_list]
                            if east_nonclust_list: tomorrow_priority_list += east_nonclust_list

                    if (away_team in ["EDM","CAL"]) & (home_team in ["LAK","ANA"]):
                        tomorrow_priority_list = long_div_season_end(clusters["CALI"] + ["ARI","VGK","COL"],tomorrow_priority_list)

                    if (away_team in ["LAK","ANA"]) & (home_team in ["EDM","CAL"]):
                        tomorrow_priority_list = long_div_season_end(clusters["NW"][:],tomorrow_priority_list)

                    if (away_team in ["MON","OTT"]) & (home_team in ["FLA","TBL"]):
                        tomorrow_priority_list = long_div_season_end(clusters["SE"] + ["NSH"], tomorrow_priority_list)

                    if (away_team in ["FLA","TBL"]) & (home_team in ["MON","OTT"]):
                        tomorrow_priority_list = long_div_season_end(["MON","OTT","TOR","BUF"], tomorrow_priority_list)

                    if (away_team in list(nhl_info[nhl_info["Conf"] =="E"].index)) & (home_team == "COL"):
                        for team in ["ARI","VGK"]:
                            if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                                tomorrow_priority_list.append(away_team+"-"+team)

                    # Purpose of this is if visitor has spare game against cluster team - try to prevent them from going somewhere way out of the way
                    if (nhl_dynamic.loc[away_team,"long_road_trip"] == 1) & (nhl_dynamic.loc[away_team,"road_trip"] < 3) & \
                    (nhl_dynamic.loc[away_team,"location"] in clusters_list) & (measure_distance(away_team,home_team) > 1396) & \
                    (not any(filter(away_str.search,tomorrow_priority_list))):
                        # first try to add teams within 1000 miles. Modified for end of season routine
                        within1000_sample = []
                        for team in nhl_info.index:
                            if measure_distance(team,away_team) < 1000:
                                within1000_sample.append(team)
                        within1000_hold = []
                        for team in within1000_sample:
                            within1000_away = re.compile(team+"-")
                            if ( (nhl_dynamic.loc[team,"long_road_trip"] == 1) & (nhl_dynamic.loc[team,"road_trip"] < 3)) | \
                            (any(filter(within1000_away.search,tomorrow_priority_list))) | (nhl_dynamic.loc[team,"homestand"] > 8):
                                within1000_hold.append(team)
                        within1000_sample = [team for team in within1000_sample if team not in within1000_hold]
                        within1000_list = [away_team+"-"+team for team in within1000_sample if away_team+"-"+team in games_played_list]
                        home500_sample = []
                        home500_hold = []
                        for team in nhl_info.index:
                            if measure_distance(team,away_team) < 500:
                                home500_sample.append(team)
                        for team in home500_sample:
                            home500_away = re.compile(team+"-")
                            if ( (nhl_dynamic.loc[team,"long_road_trip"] == 1) & (nhl_dynamic.loc[team,"road_trip"] < 3)) | \
                            (any(filter(home500_away.search,tomorrow_priority_list))) | (nhl_dynamic.loc[team,"homestand"] > 8):
                                home500_hold.append(team)
                        home500_sample = [team for team in home500_sample if team not in home500_hold]
                        home500_list = [away_team+"-"+team for team in home500_sample if away_team+"-"+team in games_played_list]
                        if home500_list: tomorrow_priority_list += home500_list
                        if within1000_list: tomorrow_priority_list += within1000_list

                daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                if any(filter(home_abbrv_str.search,priority_list)):
                    home_removed = [game for game in priority_list if re.search(home_abbrv_str,game)]
                    priority_list = [game for game in priority_list if not re.search(home_abbrv_str,game)]
                    if home_removed:
                        for game in home_removed: tomorrow_priority_list.append(game)
                if any(filter(away_abbrv_str.search,priority_list)):
                    away_removed = [game for game in priority_list if re.search(away_abbrv_str,game)]
                    priority_list = [game for game in priority_list if not re.search(away_abbrv_str,game)]
                    if away_removed:
                        for game in away_removed: tomorrow_priority_list.append(game)
                break # go to next team
            continue # go to next team

        while True:
            if (max_games == 0) | (not daily_list): # EOD
                current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                break

            if current_date in games_by_date.keys():
                if len(games_by_date[current_date]) == max_games:
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break

            if priority_list: # SCENARIO 17: There is priority list - after min GP routine (after 2023-03-29)
                for game_to_check in priority_list: # allows oldest to be dealt with first
                    away_team,home_team = get_teams_from_game(game_to_check)
                    away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                    if priority_list_exclusions(dist = 1100) == "pl remove":
                        continue
                    if game_to_check not in daily_list: continue

                   # scheduling routine 17
                    season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic = \
                    scheduling_routine_prio(season_games_list, games_played_list, priority_list, daily_list, games_by_date, tomorrow_priority_list, today_list, nhl_dynamic)
                    if len(games_by_date[current_date]) == max_games: # EOD
                        current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                        end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                        break
                    else: continue
                priority_list = [game for game in priority_list if game not in season_games_list]
                tomorrow_priority_list += priority_list
                priority_list.clear()

            else: # SCENARIO 18: No priority list (after 2023-03-29)
                if current_date in games_by_date.keys():
                    if len(games_by_date[current_date]) == max_games:
                        current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                        end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                        break
                game_to_check = random.choice(daily_list)
                away_team,home_team = get_teams_from_game(game_to_check)
                away_str, home_str, away_abbrv_str, home_abbrv_str, opposite_home_str, opposite_away_str = generate_strings()

                if reduced_nonprio() == "exclusions_list":
                    if game_to_check in daily_list: daily_list.remove(game_to_check)
                    continue

                # scheduling routine 18
                season_games_list.append(game_to_check)
                games_played_list.remove(game_to_check)
                daily_list.remove(game_to_check)
                if current_date not in games_by_date.keys():
                    games_by_date[current_date] = [game_to_check]
                else: games_by_date[current_date].append(game_to_check)
                today_list.append(away_team); today_list.append(home_team)

                nhl_dynamic = dynamic_updates(df = nhl_dynamic)

                if (measure_distance(away_team,home_team) > 1396):
                    nhl_dynamic.loc[away_team,"long_road_trip"] = 1
                    if home_team in clusters_list:
                        home_cluster = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                        home_cluster.remove(home_team)
                        for team in home_cluster:
                            if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                                tomorrow_priority_list.append(away_team+"-"+team)
                        home_cluster.append(home_team)
                    if (away_team+"-"+home_team in games_played_list) & (away_team+"-"+home_team not in tomorrow_priority_list):
                        tomorrow_priority_list.append(away_team+"-"+home_team)

                    if (away_team in pac_plus) & (home_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & \
                    (home_team not in clusters_list): # west coast team playing at non-cluster E conf team (excludes CHI, WIN, MIN) who is not going to be on priority list as visitor.
                        tomorrow_priority_list = pacplus_eastconf(tomorrow_priority_list = tomorrow_priority_list)

                if 1000 < measure_distance(away_team,home_team) < 1396:
                    if (away_team in central_west) & (nhl_info.loc[home_team,"Conf"] == "E"):
                        if home_team in clusters_list:
                            home_cluster = clusters[[cluster for cluster,teams in clusters.items() if home_team in teams][0]]
                            home_cluster.remove(home_team)
                            for team in home_cluster:
                                if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                                    tomorrow_priority_list.append(away_team+"-"+team)
                            home_cluster.append(home_team)

                        else:
                            east_sample = [team for team in list(nhl_info[nhl_info["Conf"] == "E"].index) if not team in clusters_list]
                            east_sample.remove(home_team)
                            east_hold = []
                            for team in east_sample:
                                east_away = re.compile(team+"-")
                                if (any(filter(east_away.search,priority_list))) | (any(filter(east_away.search,tomorrow_priority_list))):
                                    east_hold.append(team)
                                    continue
                                if (nhl_dynamic.loc[team,"homestand"] > 9) & (nhl_dynamic.loc[team,"away_games"] < 41):
                                    east_hold.append(team)
                                    continue
                            east_sample = [team for team in east_sample if team not in east_hold]
                            east_nonclust_list = [away_team+"-"+team for team in east_sample if away_team+"-"+team in games_played_list]
                            if east_nonclust_list: tomorrow_priority_list += random.sample(east_nonclust_list,1)

                    if (away_team == "DAL") & (home_team in north_east):
                        northeast_others = north_east[:]
                        northeast_others.remove(home_team)
                        for team in northeast_others:
                            if ("DAL-"+team in games_played_list) & ("DAL-"+team not in tomorrow_priority_list):
                                tomorrow_priority_list.append("DAL-"+team)

                    if (away_team in list(nhl_info[nhl_info["Conf"] == "E"].index)) & (home_team == "COL"):
                        for team in ["ARI","VGK"]:
                            if (away_team+"-"+team in games_played_list) & (away_team+"-"+team not in tomorrow_priority_list):
                                tomorrow_priority_list.append(away_team+"-"+team)

                daily_list = [game for game in daily_list if not re.search(home_abbrv_str,game)]
                daily_list = [game for game in daily_list if not re.search(away_abbrv_str,game)]
                if len(games_by_date[current_date]) == max_games: # EOD
                    current_date, tomorrow_priority_list, priority_list, nhl_dynamic = \
                    end_of_day(date = current_date, list1 = tomorrow_priority_list, list2 = priority_list, df = nhl_dynamic)
                    break
    if (max(nhl_dynamic.home_games) != 41) | (min(nhl_dynamic.away_games) != 41) | (len(games_played_list) != 0):
        print("Something is wrong with the program. Please check and adjust"); sys.exit(0)

    else:
        if current_date < "2023-04-22":
            print("season scheduled!")
            print("Season ends on",(pd.to_datetime(current_date) - pd.to_timedelta(1,"D")).strftime("%m-%d-%Y"),"\n")
            break
        else:
            games_played_list = season_games_list[:]
            season_games_list.clear()
            if schedule_runs == 0: print("I apologize for the delay. Please stand by...")
            elif schedule_runs == 1: print("I really am sorry, this is taking unusually long")
            elif schedule_runs == 2: print("Almost there!")
            else: print("This never happens, I swear. Please stand by...")
            schedule_runs +=1
            continue

## EXPORT SCHEDULE AS TXT FILE##
print("I will now print the full schedule to the file 'nhl_2022_2023.txt' which will be saved to the working directory \n")
with open("nhl_2022_2023.txt","w") as f:
    for gameday in games_by_date.keys():
        gameday_str = (" "*3)+gameday+(" "*3)
        s1 = "{:*^60}".format(gameday_str)
        f.write(s1+"\n\n")
        f.write("\n")
        for j in range(len(games_by_date[gameday])):
            game = games_by_date[gameday][j]
            away_abbrv = re.search("[A-Z]{3}(?=-)",game).group(0)
            home_abbrv = re.search("(?<=[A-Z]{3}-)[A-Z]{3}",game).group(0)
            game_str = "{} {} {} {} {}"
            s2 = game_str.format(nhl_info.loc[away_abbrv,"Team"],nhl_info.loc[away_abbrv,"Team_Name"],"@",\
            nhl_info.loc[home_abbrv,"Team"],nhl_info.loc[home_abbrv,"Team_Name"])
            f.write(s2+"\n\n")
        f.write("\n\n")
f.close()
