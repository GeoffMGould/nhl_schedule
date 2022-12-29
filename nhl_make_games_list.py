## PART 1 of 3 in NHL package. Generates list of all games which will be put
## into the schedule. Each item on the list is in the form of AWY-HME in which
## AWY is the 3 letter abbreviation for the away team, and HME is the 3 letter
## abbreviation for the home team.

import pandas as pd; import random

#Set working directory
# import os; #os.chdir("/Users/Geoff/Documents/Python")

# input spreadsheet with basic info
nhl_info = pd.read_csv("/Users/Geoff/Documents/Python/NHL_info.csv", index_col = "Team_Abbr")

### ***** PART 1 ***** ####
## BASIC CHECKS ON INPUT AND SETUP

## Check input CSV to make sure all fields are filled in
nhl_withnulls = nhl_info[nhl_info.isnull().any(axis=1)]
nhl_withnulls = nhl_withnulls.fillna(9999)

if len(nhl_withnulls) > 0:
    for i in range(len(nhl_withnulls)):
        nulls_dict[nhl_withnulls.index[i]] = nhl_withnulls.columns[(nhl_withnulls.iloc[i]).tolist().index(9999)]

    for team,column in nulls_dict.items():
        print(team,"has a missing value in the column entitled",'"'+column+'"')

    print("Fix missing values and try again"); exit()


## Make sure conf is only "W" or "E"
if not all(nhl_info.Conf.isin(list("WE"))):
     bad_conf_series = nhl_info.Conf.isin(["W","E"])
     bad_conf_series = bad_conf_series[bad_conf_series==False]
     bad_conf_teams = list(bad_conf_series.keys())
     print("The following teams have an incorrect entry in the 'Conf' column:")
     print(bad_conf_teams); exit()

## Make sure block is only "A", "B", "C", "D"
if not all(nhl_info.Block.isin(list("ABCD"))):
     bad_block_series = nhl_info.Block.isin(list("ABCD"))
     bad_block_series = bad_block_series[bad_block_series==False]
     bad_block_teams = list(bad_block_series.keys())
     print("The following teams have an incorrect entry in the 'Block' column:")
     print(bad_block_teams); exit()

## Make sure division is only "ATL", "CEN", "MET", "PAC"
if not all(nhl_info.Div.isin(["ATL","CEN","MET","PAC"])):
     bad_div_series = nhl_info.Div.isin(["ATL","CEN","MET","PAC"])
     bad_div_series = bad_div_series[bad_div_series==False]
     bad_div_teams = list(bad_div_series.keys())
     print("The following teams have an incorrect entry in the 'Div' column:")
     print(bad_div_teams); exit()

## Make sure team abbreviation is 3 capital letters
if not all(nhl_info.index.str.match(r"^[A-Z]{3}$")):
     bad_abbrv_series = nhl_info.index.str.match(r"^[A-Z]{3}$")
     bad_abbrv_series = pd.Series(bad_abbrv_series,index=nhl_info.Team)
     bad_abbrv_series = bad_abbrv_series[bad_abbrv_series==False]
     bad_abbrv_teams = list(bad_abbrv_series.keys())
     print("The following teams have an incorrect entry in the 'Team_Abbr' column:")
     print(bad_abbrv_teams); exit()

## Make sure state is 2 capital letters
if not all(nhl_info.State.str.match(r"^[A-Z]{2}$")):
     bad_state_series = nhl_info.State.str.match(r"^[A-Z]{2}$")
     bad_state_series = bad_state_series[bad_state_series==False]
     bad_state_teams = list(bad_state_series.keys())
     print("The following teams have an incorrect entry in the 'State' column:")
     print(bad_state_teams); exit()

## Make sure last year results have correct numbers
last_year_checks = []
last_year_checks.append(len(nhl_info[nhl_info["Last_Year"]==1])==1) # cup winner
last_year_checks.append(len(nhl_info[nhl_info["Last_Year"]==2])==1) # runner up
last_year_checks.append(len(nhl_info[nhl_info["Last_Year"]==3])==2) # other semi-finalists
last_year_checks.append(len(nhl_info[nhl_info["Last_Year"]==4])==4) # other quarter finalists
last_year_checks.append(len(nhl_info[nhl_info["Last_Year"]==5])==8) # other playoff teams
last_year_checks.append(len(nhl_info[nhl_info["Last_Year"]==6])==16) # didn't make playoffs
if not all(last_year_checks):
    print("Classification for last year's results is incorrect."); exit()
if not (nhl_info[nhl_info["Last_Year"]==1]).loc[:,"Conf"][0] != \
(nhl_info[nhl_info["Last_Year"]==2]).loc[:,"Conf"][0]:
    print("Winner and runner up should be in different conferences"); exit()
if not len(nhl_info[(nhl_info["Last_Year"] == 3) & (nhl_info["Conf"] == "W")]) == 1 & \
len(nhl_info[(nhl_info["Last_Year"] == 3) & (nhl_info["Conf"] == "E")]) == 1:
    print("There should be one team from each conference that was eliminated in the semi-finals"); exit()
if not len(nhl_info[(nhl_info["Last_Year"] == 4) & (nhl_info["Conf"] == "W")]) == 2 & \
len(nhl_info[(nhl_info["Last_Year"] == 4) & (nhl_info["Conf"] == "E")]) == 2:
    print("There should be two teams from each conference that were eliminated in the quarter-finals"); exit()
if not len(nhl_info[(nhl_info["Last_Year"] == 5) & (nhl_info["Conf"] == "W")]) == 4 & \
len(nhl_info[(nhl_info["Last_Year"] == 5) & (nhl_info["Conf"] == "E")]) == 4:
    print("There should be four teams from each conference that were eliminated in the first round"); exit()
if not len(nhl_info[(nhl_info["Last_Year"] == 6) & (nhl_info["Conf"] == "W")]) == 8 & \
len(nhl_info[(nhl_info["Last_Year"] == 6) & (nhl_info["Conf"] == "E")]) == 8:
    print("There should be eight teams from each conference that didn't make the playoffs"); exit()

# define constant and list
FULL_SCHEDULE = int(82 * len(nhl_info) / 2)
games_played_list = []

# adds geographical information to input spreadsheet
us_cities = pd.read_csv("/Users/Geoff/Documents/Python/uscities.csv")
canada_cities = pd.read_csv("/Users/Geoff/Documents/Python/canadacities.csv")
us_cities = us_cities[["city","state_id","lat","lng"]]
canada_cities = canada_cities[["city_ascii","province_id","lat","lng"]] # need ascii for accent in Montréal
us_cities = us_cities.rename(columns={"state_id":"State","city":"City"})
canada_cities = canada_cities.rename(columns={"province_id":"State","city_ascii":"City"})
north_amer_cities = pd.concat([us_cities,canada_cities])
nhl_geo = pd.merge(nhl_info,north_amer_cities, on=["City","State"])
nhl_geo = nhl_geo.set_index(nhl_info.index)
nhl_info = nhl_geo
teams_list = list(nhl_info.index)

### ***** PART 2 ***** ####
## DEFINE FUNCTIONS

def check_and_sked_game(n):
    """ CUTS OUT REPITITIVE LINES """
    if games_played_list.count(away_team+"-"+home_team) < n:
        new_game = away_team+"-"+home_team
        return new_game

def same_conf_diff_div1(): # MET AND CEN
   """ SCHEDULES GAMES BETWEEN TEAMS IN THE SAME CONFERENCE BUT IN DIFFERENT DIVISIONS.
   SCHEDULES GAMES WHEN A TEAM IN THE 'REFERENCE DIVISION' FOR A CONFERENCE IS CHOSEN AS THE HOME TEAM.
   ALSO REPLACES REPETITIVE CODE."""
   if nhl_info.loc[home_team,"Block"] <= "B": # ref blocks A & B
       if nhl_info.loc[away_team,"Block"] <= "B":  # other blocks A & B
           return check_and_sked_game(2)
       else: # other blocks C & D
           return check_and_sked_game(1)

   else: # MET blocks C & D
       if nhl_info.loc[away_team,"Block"] > "B": # other blocks C & D
           return check_and_sked_game(2)
       else: # other blocks C & D
           return check_and_sked_game(1)

def same_conf_diff_div2(): #ATL and PAC
   """ SCHEDULES GAMES BETWEEN TEAMS IN THE SAME CONFERENCE BUT IN DIFFERENT DIVISIONS.
   SCHEDULES GAMES WHEN A TEAM IN THE COMPLEMENT OF THE REFERENCE DIVISION IS CHOSEN AS THE HOME TEAM
   ALSO REPLACES REPETITIVE CODE."""
   if nhl_info.loc[home_team,"Block"] <= "B": # ref blocks A & B
       if nhl_info.loc[away_team,"Block"] <= "B":  # other blocks A & B
           return check_and_sked_game(1)
       else: # ref blocks C & D
           return check_and_sked_game(2)

   else: # other blocks C & D
       if nhl_info.loc[away_team,"Block"] > "B": # ATL blocks C & D
           return check_and_sked_game(1)
       else: # ref blocks C & D
           return check_and_sked_game(2)

def sked_crossblock_games():
    """ SCHEDULES GAMES BETWEEN TEAMS IN THE SAME DIVISION AND ARE IN BLOCKS THAT
    RESULT IN THEM PLAYING 3 TIMES A YEAR INSTEAD OF 4 (I.E. A&B OR C&D). ALSO REPLACES REPETITIVE CODE."""
    if (away_team+"-"+home_team) not in games_played_list:
        new_game = away_team+"-"+home_team
        return new_game
    else:
        if nhl_info.loc[home_team,"Crossblock_Ref"] == 0:   # identifies as first duplicate x-block game
            new_game = away_team+"-"+home_team
            home_other_crossblock = nhl_info[(nhl_info.Div == nhl_info.loc[away_team,"Div"]) & \
            (nhl_info.Block == nhl_info.loc[away_team,"Block"]) & (nhl_info.index != away_team)]
            home_other_crossblock = list(home_other_crossblock.index)[0]
            away_other_crossblock = nhl_info[(nhl_info.Div == nhl_info.loc[away_team,"Div"]) & \
            (nhl_info.Block == nhl_info.loc[home_team,"Block"]) & (nhl_info.index != home_team)]
            away_other_crossblock = list(away_other_crossblock.index)[0]
            nhl_info.loc[away_team, "Crossblock_Ref"] = "away_ref"
            nhl_info.loc[home_team, "Crossblock_Ref"] = "home_ref"
            nhl_info.loc[away_other_crossblock, "Crossblock_Ref"] = "away_xbref"
            nhl_info.loc[home_other_crossblock, "Crossblock_Ref"] = "home_xbref"
            return new_game
        else:
            if nhl_info.loc[away_team, "Crossblock_Ref"] == "away_ref":
                if nhl_info.loc[home_team, "Crossblock_Ref"] == "away_xbref":
                    return check_and_sked_game(1)
            if nhl_info.loc[away_team, "Crossblock_Ref"] == "home_ref":
                if nhl_info.loc[home_team, "Crossblock_Ref"] == "away_ref":
                    return check_and_sked_game(1)
                elif nhl_info.loc[home_team, "Crossblock_Ref"] == "home_xbref":
                    return check_and_sked_game(2)
            if nhl_info.loc[away_team, "Crossblock_Ref"] == "away_xbref":
                if nhl_info.loc[home_team, "Crossblock_Ref"] == "home_xbref":
                    return check_and_sked_game(1)
                elif nhl_info.loc[home_team, "Crossblock_Ref"] == "away_ref":
                    return check_and_sked_game(2)
            elif nhl_info.loc[away_team, "Crossblock_Ref"] == "home_xbref":
                if nhl_info.loc[home_team, "Crossblock_Ref"] == "home_ref":
                    return check_and_sked_game(1)
                elif nhl_info.loc[home_team, "Crossblock_Ref"] == "away_xbref":
                    return check_and_sked_game(2)

### ***** PART 3 ***** ####
#GENERATES ALL 1312 GAMES FOR SEASON IN AWY-HME FORM AND ADDS THEM TO GAMES_PLAYED_LIST
while len(games_played_list) < FULL_SCHEDULE:
 teams_list_for_sample = teams_list[:]
 home_team = random.choice(teams_list_for_sample)
 teams_list_for_sample.remove(home_team)
 away_team = random.choice(teams_list_for_sample)

 if nhl_info.loc[home_team,"Conf"] != nhl_info.loc[away_team,"Conf"]:
    if games_played_list.count(away_team+"-"+home_team) < 1:
        games_played_list.append(away_team+"-"+home_team)
    else: continue

# same conference different division
 elif (nhl_info.loc[home_team,"Div"] != nhl_info.loc[away_team,"Div"]) & \
     (nhl_info.loc[home_team,"Conf"] == nhl_info.loc[away_team,"Conf"]):
         if (nhl_info.loc[home_team,"Div"] == "MET") | \
         (nhl_info.loc[home_team,"Div"] == "CEN"):
             new_game = same_conf_diff_div1()
             if new_game:
                 games_played_list.append(new_game)
             else: continue

         elif (nhl_info.loc[home_team,"Div"] == "ATL") | \
         (nhl_info.loc[home_team,"Div"] == "PAC"):  # using ATL or PAC division as reference
               new_game = same_conf_diff_div2()
               if new_game:
                 games_played_list.append(new_game)
               else: continue

# same division
 else:
     if nhl_info.loc[home_team,"Block"] <= "B": # if home is in block A or B
         if (nhl_info.loc[away_team,"Block"] > "B") | (nhl_info.loc[home_team,"Block"] == nhl_info.loc[away_team,"Block"]): # and away is in block C or D, or if both are in the same block (A-A & B-B) they play 4 games, 2 at each team
             if games_played_list.count(away_team+"-"+home_team) < 2:
                 games_played_list.append(away_team+"-"+home_team)
                 continue
         else:
                 new_game = sked_crossblock_games()
                 if new_game:
                     games_played_list.append(new_game)
                 else: continue
     else: # home team block is C or D
          if (nhl_info.loc[away_team,"Block"] <= "B") | (nhl_info.loc[home_team,"Block"] == nhl_info.loc[away_team,"Block"]): #if away is in block A or B, or if both are in the same block (C-C & D-D) they play 4 games, 2 at each team
               if games_played_list.count(away_team+"-"+home_team) < 2:
                   games_played_list.append(away_team+"-"+home_team)
                   continue
          else:
                  new_game = sked_crossblock_games()
                  if new_game:
                      games_played_list.append(new_game)
                  else: continue
