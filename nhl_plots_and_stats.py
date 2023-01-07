## 3 of 3 in NHL package. Generates figures comparing travel by
## team, division, and conference. Runs statistical tests comparing travel by
## division and conference

import pandas as pd; import matplotlib.pyplot as plt
import matplotlib.patches as mpatches; import matplotlib.lines as mlines
from scipy.stats import ttest_ind, kruskal, shapiro, mannwhitneyu, f_oneway
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from nhl_make_schedule import games_by_date
from nhl_make_schedule import nhl_info
from nhl_make_schedule import measure_distance
import re; import sys
import statsmodels.api as sm

######*** PART 1 ****###
#SETUP
season_games_df = pd.DataFrame(0, index = list(range(1,5)), columns = ["Date", "Game"])
rows = 1
for gameday in games_by_date.keys():
    for i in range(len(games_by_date[gameday])):
        season_games_df.loc[rows,"Date"] = gameday
        season_games_df.loc[rows,"Game"] = games_by_date[gameday][i]
        rows += 1
season_games_df[["Away","Home"]] = season_games_df.Game.str.split("-",expand = True)

season_games_df.to_csv("nhl_2022_2023_schedule.csv") # generate schedule in csv form

for team in nhl_info.index:
     team_df = season_games_df[(season_games_df.Away == team) | (season_games_df.Home == team)]
     team_home = list(team_df.Home)
     miles_traveled = 0
     for i in range(len(team_home)-1):
        miles_traveled += measure_distance(team_home[i],team_home[i+1])
     nhl_info.loc[team,"Miles"] = miles_traveled

mean_miles = pd.DataFrame(nhl_info.groupby("Div")["Miles"].mean())# - gets average miles traveled by division
std_miles = pd.DataFrame(nhl_info.groupby("Div")["Miles"].std()) # - gets standard dev of miles traveled by division
mean_miles = mean_miles.rename(columns={"Miles":"Mean"})
std_miles = std_miles.rename(columns={"Miles":"SD"})
travel_by_div = pd.concat([mean_miles,std_miles],axis=1)

#travel_by_div = pd.read_csv("/Users/Geoff/Documents/Python/travelbydiv.csv", index_col = "Div")
nhl_plot1 = nhl_info
nhl_plot1 = nhl_plot1.sort_values("Miles")
nhl_miles = nhl_plot1[["Div","Conf","Miles"]]
conference_dict = {"E":"Eastern", "W":"Western"}

travel_by_div = travel_by_div.sort_values("Mean")

x = nhl_plot1.index
y = nhl_plot1.Miles

# PLOT 1 - horizontal bar plot
# color families getting lighter frop top to bottom to be easier on the eyes than a single color for each division
# preserved top to bottom order of colors regardless of how individual schedule turns out
def make_horizontal_bar_plot():
    """GENERATES IMAGE FILE OF HORIZONTAL BAR PLOT COMPARING TRAVEL BETWEEN
    ALL TEAMS, COLOR CODED BY DIVISION"""
    zero_count = 0; one_count = 0; two_count = 0; three_count = 0
    zero_colors = ["#4397f8","#308df7","#1d82f6","#0a78f5","#096ee3","#0865d0","#075cbd","#0753aa"]
    one_colors = ["#000000","#292929","#1f1f1f", "#161616","#0f1416","#0c0c0c","#090c0d","#020202"]
    two_colors = ["#9f9f9f", "#959595","#8b8b8b","#818181","#787878","#6e6e6e","#646464","#5a5a5a"]
    three_colors = ["#f53b28","#f42a15","#ec1f0b","#d91c0a","#c61a09","#b31808","#a01507","#8e1306"]

    x = nhl_plot1.index
    y = nhl_plot1.Miles

    plot1_colors = []
    for i in range(len(nhl_plot1.index)):
        if nhl_plot1.loc[nhl_plot1.index[i],"Div"] == travel_by_div.index[0]:
            plot1_colors.append(zero_colors[zero_count])
            zero_count += 1
        elif nhl_plot1.loc[nhl_plot1.index[i],"Div"] == travel_by_div.index[1]:
            plot1_colors.append(one_colors[one_count])
            one_count += 1
        elif nhl_plot1.loc[nhl_plot1.index[i],"Div"] == travel_by_div.index[2]:
            plot1_colors.append(two_colors[two_count])
            two_count += 1
        elif nhl_plot1.loc[nhl_plot1.index[i],"Div"] == travel_by_div.index[3]:
            plot1_colors.append(three_colors[three_count])
            three_count += 1

    patch_0 = mpatches.Patch(color = "#4397f8", label = travel_by_div.index[0])
    patch_1 = mpatches.Patch(color = "#000000", label = travel_by_div.index[1])
    patch_2 = mpatches.Patch(color = "#9f9f9f", label = travel_by_div.index[2])
    patch_3 = mpatches.Patch(color = "#f53b28", label = travel_by_div.index[3])

    fig, ax = plt.subplots()
    fig.set_size_inches(15,12)
    ax.bar_label(ax.barh(x,y,color = plot1_colors, height = .6, align= "edge"), labels = list(nhl_plot1.index), \
    label_type="edge",padding = -28, color="white", fontweight="bold", fontsize = 10)
    ax.tick_params(left = False)
    ax.axes.yaxis.set_ticklabels([])
    ax.set_title("Miles Traveled by Team for 2022-2023 Season", y = 1.025, fontsize = 20)
    ax.set_xlabel("Miles", fontsize = 16, labelpad = 12.5)
    ax.grid(which = "major", axis = "x", color="darkslategrey",linewidth = .5)
    ax.set_facecolor("aliceblue")
    ax.legend(handles = [patch_3,patch_2,patch_1,patch_0], title = "Division", \
    edgecolor = "black", framealpha = 1, title_fontsize = 14, prop = {"size" : 12}, borderpad = 1.3, \
    borderaxespad = 1.7, handletextpad = 1)

    print("Saving to working directory as 'horizontal_bar_plot.png'")
    print("This usually takes about 15-20 seconds because of the high resolution. Please stand by...")
    plt.savefig("horizontal_bar_plot.png", dpi = 1200)
    #plt.show()

# PLOT 2 - simple errorbar plot for general audiences
def make_errorbar_plot():
    """GENERATES IMAGE FILE OF ERROR BAR PLOT COMPARING TRAVEL BETWEEN DIVISIONS"""
    x = travel_by_div.index
    y = travel_by_div.Mean
    yerr_list = []
    for div in travel_by_div.index:
        yerr_list.append(travel_by_div.loc[div,"SD"])
    fig, axs = plt.subplots()
    axs.errorbar(x,y,yerr = yerr_list, fmt = 'o', color = "black", ecolor = ["darkred","darkred","black","black"])
    axs.set_ylabel("Miles", fontsize = 20, labelpad = 16)
    axs.set_title("Miles Traveled on Average by Teams\n by Division in 2022-2023 Season", fontsize = 24, y = 1.025)
    axs.grid(axis = "y", color = "white", linewidth = .25)
    axs.set_facecolor("#a4a9ad") # hex color from NHL shield
    leg_line1 = mlines.Line2D([],[], color = "darkred", marker = "o", markerfacecolor = "black", markeredgecolor = "black", label = "Eastern")
    leg_line2 =  mlines.Line2D([],[], color = "black", marker = "o", markerfacecolor = "black", label = "Western")
    axs.legend(handles = [leg_line1,leg_line2], loc = "lower right", title = "Conference", edgecolor = "black", \
    title_fontsize = 14, borderaxespad = 1, borderpad = 1.3, framealpha = 1)

    print("Saving to working directory as 'error_bar_plot.png'")
    print("This usually takes about 5-10 seconds because of the high resolution...")
    plt.savefig("error_bar_plot.png", dpi = 1200)
    #plt.show()

# PLOT 3 - Boxplot for the more statistically minded
def make_boxplot():
    """GENERATES IMAGE FILE OF BOXPLOT COMPARING TRAVEL BETWEEN DIVISIONS"""
    atl_miles = nhl_plot1[nhl_plot1["Div"] == "ATL"]["Miles"]
    cen_miles = nhl_plot1[nhl_plot1["Div"] == "CEN"]["Miles"]
    met_miles = nhl_plot1[nhl_plot1["Div"] == "MET"]["Miles"]
    pac_miles = nhl_plot1[nhl_plot1["Div"] == "PAC"]["Miles"]
    whisk_colors = ["darkred"] * 4 + ["black"] * 4
    box_edge_colors = ["darkred"] * 2 + ["black"] * 2

    fig2, axs2 = plt.subplots()
    flierprops = dict(marker = "o", markeredgecolor = "black")
    bp = axs2.boxplot(x = [met_miles,atl_miles,pac_miles,cen_miles], vert = True, patch_artist = True, flierprops = flierprops)
    plt.setp(bp["boxes"], color="#a4a9ad")
    for i in range(len(bp["boxes"])):
        plt.setp(bp["boxes"][i], edgecolor = box_edge_colors[i])
    plt.setp(bp["medians"], color="white")

    for element in ("whiskers", "caps"):
        for patch,color in zip(bp[element],whisk_colors):
            patch.set(color=color)
    axs2.set_xticklabels(labels = ["MET","ATL","PAC","CEN"])
    axs2.set_title("Miles Traveled on Average by Teams\n by Division in 2022-2023 Season", fontsize = 24, y = 1.025)
    axs2.grid(axis = "y", color = "white", linewidth = .25)
    axs2.set_xlabel("Division", fontsize = 20, labelpad = 16)
    axs2.set_ylabel("Miles", fontsize = 20, labelpad = 16)
    axs2.set_facecolor("#a4a9ad")
    leg_line1 = mlines.Line2D([],[], color = "darkred", marker = "s", markerfacecolor = "#a4a9ad", \
    markeredgecolor = "darkred", label = "Eastern", markersize = 10)
    leg_line2 =  mlines.Line2D([],[], color = "black", marker = "s", markerfacecolor = "#a4a9ad", \
    label = "Western", markersize = 10)
    axs2.legend(handles = [leg_line1,leg_line2], loc = "upper left", title = "Conference", edgecolor = "black", \
    title_fontsize = 14, borderaxespad = 1, borderpad = 1.3, framealpha = 1)

    print("Saving to working directory as 'boxplot.png'")
    print("This usually takes about 5 seconds because of the high resolution...")
    plt.savefig("boxplot.png", dpi = 1200)
    #plt.show()

## PLOT 4 - QQ Plots - for use in divisional comparison (ANOVA/Kruskal-Wallis)
def make_qq_plot():
    """GENERATES IMAGE OF QQ PLOTS FOR MILES TRAVLED BY ALL DIVISIONS. USED
    IN STATISTICAL COMPARISON OF TRAVEL BY DIVISION"""

    atl_miles = nhl_plot1[nhl_plot1["Div"] == "ATL"]["Miles"]
    cen_miles = nhl_plot1[nhl_plot1["Div"] == "CEN"]["Miles"]
    met_miles = nhl_plot1[nhl_plot1["Div"] == "MET"]["Miles"]
    pac_miles = nhl_plot1[nhl_plot1["Div"] == "PAC"]["Miles"]

    fig = plt.figure()
    fig.suptitle("QQ Plots for Miles Traveled by Division",fontsize = 16)

    ax = fig.add_subplot(2, 2, 1)
    sm.graphics.qqplot(atl_miles, line = "45", ax=ax, fit=True)
    ax.set_title("Atlantic")
    ax.set_xlim(-2, 2)
    ax.set_xlabel("")
    ax.axes.xaxis.set_ticklabels([])

    ax = fig.add_subplot(2, 2, 2)
    sm.graphics.qqplot(cen_miles, line='45', ax=ax, fit=True)
    ax.set_title("Central")
    ax.set_xlim(-2, 2)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.axes.xaxis.set_ticklabels([])

    ax = fig.add_subplot(2, 2, 3)
    sm.graphics.qqplot(pac_miles, line='45', ax=ax, fit=True)
    ax.set_title("Pacific")
    ax.set_xlim(-2, 2)

    ax = fig.add_subplot(2, 2, 4)
    sm.graphics.qqplot(met_miles, line='45', ax=ax, fit=True)
    ax.set_title("Metropolitan")
    ax.set_xlim(-2, 2)
    ax.set_ylabel("")

    fig.tight_layout()

    print("Saving to working directory as 'nhl_qqplots.png'")
    plt.savefig("nhl_qqplots.png", dpi=600) # not as concerned about resolution on this one

####*** PART 3 ****###
#STATS
# Statistical tests for difference in travel between conferences
def conference_comparison():
    """USES A T-TEST OR MANN-WHITNEY U TEST TO COMPARE TRAVEL BETWEEN
    CONFERENCES AFTER CHECKING FOR NORMALITY"""
    east_miles = nhl_plot1[nhl_plot1["Conf"] == "E"]
    west_miles = nhl_plot1[nhl_plot1["Conf"] == "W"]

    if (shapiro(east_miles["Miles"])[1] < 0.05) | ((shapiro(west_miles["Miles"])[1] < 0.05)):
        print("Data is non-parametric. Will compare with Mann-Whitney Test")
        mwu_pvalue = mannwhitneyu(east_miles["Miles"], west_miles["Miles"])[1]

        if mwu_pvalue < 0.05:
            print("Result:",conference_dict[nhl_plot1.groupby("Conf")["Miles"].mean().sort_values(ascending=False).index[0]],"conference travels more\n p-value:",\
            mwu_pvalue,"\n")
        else:
            print("Result: No significant difference in miles traveled between conferences, p-value:",mwu_pvalue,"\n")

    else:
        print("Comparing travel between conferences with a regular old t-test")
        east_west_miles = ttest_ind(east_miles["Miles"], west_miles["Miles"])
        if east_west_miles[1] >= 0.05:
            print("Result: No significant difference in miles traveled between conferences, p-value: (",east_west_miles[1],")\n")
        else:
            print("Result:",conference_dict[nhl_plot1.groupby("Conf")["Miles"].mean().sort_values(ascending=False).index[0]],"conference travels more (p-value:",\
            east_west_miles[1],")\n")

# Statistical tests for difference in travel between divisions
def division_comparison():
    """USES ANOVA OR KRUSKAL-WALLIS TEST TO CHECK IF THERE ARE SIGNIFICANT
    DIFFERENCES IN TRAVEL BY DIVISION. CHECKS FOR NORMALITY AND OFFERS OPTION
    OF QQ PLOTS."""
    atl_miles = nhl_plot1[nhl_plot1["Div"] == "ATL"]
    cen_miles = nhl_plot1[nhl_plot1["Div"] == "CEN"]
    met_miles = nhl_plot1[nhl_plot1["Div"] == "MET"]
    pac_miles = nhl_plot1[nhl_plot1["Div"] == "PAC"]

    division_miles_shapiro = []
    for division_miles in [atl_miles,cen_miles,met_miles,pac_miles]:
        division_miles_shapiro.append(shapiro(division_miles["Miles"])[1] < 0.05)

    if any(division_miles_shapiro):
        print("Data is not parametric. Will compare divisions with Kruskal-Wallis test")
        f_stat, p_value = kruskal(atl_miles["Miles"], cen_miles["Miles"], met_miles["Miles"], pac_miles["Miles"])
        if p_value >= 0.05:
            print("Result: No significant difference in miles traveled between divisions (p-value:",p_value,")\n")
        else:
            print("Result: Some significant difference in miles traveled between divisions (p-value:",p_value,")\n")

    else:
        print("Comparing travel between divisions with ANOVA\n")
        f_stat, p_value = f_oneway(atl_miles["Miles"], cen_miles["Miles"], met_miles["Miles"], pac_miles["Miles"])
        if p_value >= 0.05:
            print("Result: No significant difference in miles traveled between divisions (p-value:",p_value,")\n")
        else:
            print("Result: Some significant difference in miles traveled between divisions (p-value:",p_value,")\n")
            print("Let's see which divisions are different from each other:\n")
            print("In the following, if 'reject' is true, it means the divisions are significantly different from each other:\n" )

        # TUKEY HSD POST-HOC FOR ANOVA
            tukey = pairwise_tukeyhsd(endog = nhl_miles["Miles"], groups = nhl_miles["Div"], alpha = 0.05)
            print(tukey)

def counter():
    """HANDLES UNRECOGNIZED INPUT AND QUITS PROGRAM IF TOO MANY ARE RECEIVED"""
    if (attempts_counter == 0):
        print("Input not recognized.\n")
        return "add1"
    elif (attempts_counter == 1):
        print("Input not recognized - program will exit if next input isn't recognized\n")
        return "add1"
    else:
        print("Program exiting now. Goodbye")
        return "exit"

attempts_counter = 0
#Prompt for plots
print("Let's look at some plots and stats\n")
print("At any time, enter 'Q' to quit the program")
while True:
    inp = input("Would you like to see plots based on distance traveled by all teams? (Y/N)\n")
    if re.search("^(\s)*[Yy](\s)*$",inp): # yes, see plots
        attempts_counter = 0
        print("Great - which one would you like to see first?\n")
        while True:
            inp_plot_choice = input("""1. Horizontal Bar Plot comparing travel for all teams \n
2. Simple Error Bar Plot comparing travel by division \n
3. Box Plot comparing travel by division\n""")
            if re.search("^(\s)*1(\s)*$",inp_plot_choice): # this level of indent is first plot choice (1)
                attempts_counter = 0
                make_horizontal_bar_plot()
                while True:
                    inp_follow_up1_yn = input("Would you like to see the errorbar plot or boxplot? (Y/N)\n") # follow up after original choice 1
                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up1_yn):
                        attempts_counter = 0
                        print("Which one?")
                        while True:
                            inp_follow_up1 = input("""1. Error Bar Plot\n2. Boxplot\n""")
                            if re.search("^(\s)*1(\s)*$",inp_follow_up1):
                                attempts_counter = 0
                                make_errorbar_plot()
                                while True:
                                    inp_follow_up11_yn = input("Would you like to see the box plot too? (Y/N)\n")
                                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up11_yn):  # choice order 1-1
                                        attempts_counter = 0
                                        make_boxplot(); break
                                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up11_yn):
                                        attempts_counter = 0
                                        print("OK. On to the stats then"); break
                                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up11_yn):
                                        print("Goodbye")
                                        sys.exit(0)
                                    else:
                                        if counter() == "add1":
                                            attempts_counter += 1
                                            continue
                                        else:
                                            sys.exit(0)
                                break
                            elif re.search("^(\s)*2(\s)*$",inp_follow_up1): # choice order 1-2
                                attempts_counter = 0
                                make_boxplot()
                                while True:
                                    inp_follow_up12_yn = input("Would you like to see the errorbar plot too? (Y/N)\n")
                                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up12_yn):
                                        attempts_counter = 0
                                        make_errorbar_plot(); break
                                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up12_yn):
                                        attempts_counter = 0
                                        print("OK. On to the stats then"); break
                                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up12_yn):
                                        print("Goodbye")
                                        sys.exit(0)
                                    else:
                                        if counter() == "add1":
                                            attempts_counter += 1
                                            continue
                                        else:
                                            sys.exit(0)
                                break
                            elif re.search("^(\s)*[Q](\s)*$",inp_follow_up1):
                                print("Goodbye")
                                sys.exit(0)
                            else:
                                if counter() == "add1":
                                    attempts_counter += 1
                                    continue
                                else:
                                    sys.exit(0)
                        break
                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up1_yn):
                        attempts_counter = 0
                        print("OK. On to the stats then")
                        break
                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up1_yn):
                        attempts_counter = 0
                        print("Goodbye")
                        sys.exit(0)
                    else:
                        if counter() == "add1":
                            attempts_counter += 1
                            continue
                        else:
                            sys.exit(0)
                break

            elif re.search("^(\s)*2(\s)*$",inp_plot_choice): # this level of indent is first plot choice (2)
                attempts_counter = 0
                make_errorbar_plot()
                while True:
                    inp_follow_up2_yn = input("Would you like to see the horizontal bar plot or box plot? (Y/N)\n") # follow up after original choice 2
                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up2_yn):
                        attempts_counter = 0
                        print("Which one?")
                        while True:
                            inp_follow_up2 = input("""1. Horizontal Bar Plot\n2. Boxplot\n""")
                            if re.search("^(\s)*1(\s)*$",inp_follow_up2): # choice order 2-1
                                attempts_counter = 0
                                make_horizontal_bar_plot()
                                while True:
                                    inp_follow_up21_yn = input("Would you like to see the box plot too? (Y/N)\n")
                                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up21_yn):
                                        attempts_counter = 0
                                        make_boxplot(); break
                                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up21_yn):
                                        attempts_counter = 0
                                        print("OK. On to the stats then"); break
                                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up21_yn):
                                        print("Goodbye")
                                        sys.exit(0)
                                    else:
                                        if counter() == "add1":
                                            attempts_counter += 1
                                            continue
                                        else:
                                            sys.exit(0)
                                break
                            elif re.search("^(\s)*2(\s)*$",inp_follow_up2): # choice order 2-2
                                attempts_counter = 0
                                make_boxplot()
                                while True:
                                    inp_follow_up12_yn = input("Would you like to see the errorbar plot too? (Y/N)\n")
                                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up22_yn):
                                        attempts_counter = 0
                                        make_errorbar_plot(); break
                                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up22_yn):
                                        attempts_counter = 0
                                        print("OK. On to the stats then"); break
                                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up22_yn):
                                        attempts_counter = 0
                                        print("Goodbye")
                                        sys.exit(0)
                                    else:
                                        if counter() == "add1":
                                            attempts_counter += 1
                                            continue
                                        else:
                                            sys.exit(0)
                                break
                            elif re.search("^(\s)*[Q](\s)*$",inp_follow_up2):
                                attempts_counter = 0
                                print("Goodbye")
                                sys.exit(0)
                            else:
                                if counter() == "add1":
                                    attempts_counter += 1
                                    continue
                                else:
                                    sys.exit(0)
                        break
                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up2_yn):
                        attempts_counter = 0
                        print("OK. On to the stats then")
                        break
                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up2_yn):
                        print("Goodbye")
                        sys.exit(0)
                    else:
                        if counter() == "add1":
                            attempts_counter += 1
                            continue
                        else:
                            sys.exit(0)
                break

            elif re.search("^(\s)*3(\s)*$",inp_plot_choice): # this level of indent is first plot choice (3)
                attempts_counter = 0
                make_boxplot()
                while True:
                    inp_follow_up3_yn = input("Would you like to see the horizontal bar plot or box plot? (Y/N)\n") # follow up after original choice 3
                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up3_yn):
                        attempts_counter = 0
                        print("Which one?")
                        while True:
                            inp_follow_up3 = input("""1. Horizontal Bar Plot\n2. Error Bar Plot\n""")
                            if re.search("^(\s)*1(\s)*$",inp_follow_up3): # choice order 3-1
                                attempts_counter = 0
                                make_horizontal_bar_plot()
                                while True:
                                    inp_follow_up31_yn = input("Would you like to see the error bar plot too? (Y/N)\n")
                                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up31_yn):
                                        attempts_counter = 0
                                        make_errorbar_plot(); break
                                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up31_yn):
                                        attempts_counter = 0
                                        print("OK. On to the stats then"); break
                                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up31_yn):
                                        print("Goodbye")
                                        sys.exit(0)
                                    else:
                                        if counter() == "add1":
                                            attempts_counter += 1
                                            continue
                                        else:
                                            sys.exit(0)
                                break
                            elif re.search("^(\s)*2(\s)*$",inp_follow_up3): # choice order 3-2
                                attempts_counter = 0
                                make_errorbar_plot()
                                while True:
                                    inp_follow_up32_yn = input("Would you like to see the horizontal bar plot too? (Y/N)\n")
                                    if re.search("^(\s)*[Yy](\s)*$",inp_follow_up32_yn):
                                        attempts_counter = 0
                                        make_horizontal_bar_plot(); break
                                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up32_yn):
                                        attempts_counter = 0
                                        print("OK. On to the stats then"); break
                                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up32_yn):
                                        print("Goodbye")
                                        sys.exit(0)
                                    else:
                                        if counter() == "add1":
                                            attempts_counter += 1
                                            continue
                                        else:
                                            sys.exit(0)
                                break
                            elif re.search("^(\s)*[Q](\s)*$",inp_follow_up3):
                                print("Goodbye")
                                sys.exit(0)
                            else:
                                if counter() == "add1":
                                    attempts_counter += 1
                                    continue
                                else:
                                    sys.exit(0)
                        break
                    elif re.search("^(\s)*[Nn](\s)*$",inp_follow_up3_yn):
                        attempts_counter = 0
                        print("OK. On to the stats then")
                        break
                    elif re.search("^(\s)*[Qq](\s)*$",inp_follow_up3_yn):
                        print("Goodbye")
                        sys.exit(0)
                    else:
                        if counter() == "add1":
                            attempts_counter += 1
                            continue
                        else:
                            sys.exit(0)
                break
            elif re.search("^(\s)*[Qq](\s)*$",inp_plot_choice): # first plot choice
                print("Goodbye")
                sys.exit(0)
            else:
                if counter() == "add1":
                    attempts_counter += 1
                    continue
                else:
                    sys.exit(0)
        break

    elif re.search("^(\s)*[Nn](\s)*$",inp): # No, don't see plots
        attempts_counter = 0
        print("OK. On to the stats then")
        break

    elif re.search("^(\s)*[Qq](\s)*$",inp):
        print("Goodbye")
        sys.exit(0)

    else:
        if counter() == "add1":
            attempts_counter += 1
            continue
        else:
            sys.exit(0)

# Prompt for statistical analysis
while True:
    inp_see_stats = input("Would you like to see some statistical comparisons of travel? (Y/N)\n")
    if re.search("^(\s)*[Yy](\s)*$",inp_see_stats):
        attempts_counter = 0
        print("Great - do you want to see a comparison by conference or divsion?")
        while True:
            inp_stats_choice = input("1. By conference\n2. By division\n")
            if re.search("^(\s)*1(\s)*$",inp_stats_choice):
                attempts_counter = 0
                conference_comparison()
                while True:
                    stats_follow_up1 = input("Would you like to see the comparison by division too? (Y/N)\n")
                    if re.search("^(\s)*[Yy](\s)*$",stats_follow_up1):
                        attempts_counter = 0
                        division_comparison()
                        while True:
                            qq_prompt = input("Would you like to see the QQ plots for the divisions? (Y/N)\n")
                            if re.search("^(\s)*[Yy](\s)*$",qq_prompt):
                                make_qq_plot()
                                print("Saving to working directory as 'nhl_qqplots.py'")
                                print("That's all for now! Goodbye!")
                                sys.exit(0)
                            elif re.search("^(\s)*[Nn](\s)*$",qq_prompt):
                                print("That's all for now! Goodbye!")
                                sys.exit(0)
                            elif re.search("^(\s)*[Qq](\s)*$",qq_prompt):
                                print("That's all for now! Goodbye!")
                                sys.exit(0)
                            else:
                                if counter() == "add1":
                                    attempts_counter += 1
                                    continue
                                else:
                                    sys.exit(0)
                    elif re.search("^(\s)*[Nn](\s)*$",stats_follow_up1):
                        print("That's all for now! Goodbye!")
                        sys.exit(0)
                    elif re.search("^(\s)*[Qq](\s)*$",stats_follow_up1):
                        print("Ok then. Goodbye!")
                        sys.exit(0)
                    else:
                        if counter() == "add1":
                            attempts_counter += 1
                            continue
                        else:
                            sys.exit(0)
                break
            elif re.search("^(\s)*2(\s)*$",inp_stats_choice):
                attempts_counter = 0
                division_comparison()
                while True:
                    qq_prompt = input("Would you like to see the QQ plots for the divisions? (Y/N)\n")
                    if re.search("^(\s)*[Yy](\s)*$",qq_prompt):
                        attempts_counter = 0
                        make_qq_plot()
                        print("Saving to working directory as 'nhl_qqplots.py'")
                        break
                    elif re.search("^(\s)*[Nn](\s)*$",qq_prompt):
                        attempts_counter = 0
                        break
                    elif re.search("^(\s)*[Qq](\s)*$",qq_prompt):
                        print("Ok then. Goodbye!")
                        sys.exit(0)
                    else:
                        if counter() == "add1":
                            attempts_counter += 1
                            continue
                        else:
                            sys.exit(0)
                while True:
                    stats_follow_up2 = input("Would you like to see the comparison by conference too? (Y/N)\n")
                    if re.search("^(\s)*[Yy](\s)*$",stats_follow_up2):
                        conference_comparison()
                        print("That's all for now! Goodbye!")
                        sys.exit(0)
                    elif re.search("^(\s)*[Nn](\s)*$",stats_follow_up2):
                        print("That's all for now! Goodbye!")
                        sys.exit(0)
                    elif re.search("^(\s)*[Qq](\s)*$",stats_follow_up2):
                        print("Ok then. Goodbye!")
                        sys.exit(0)
                    else:
                        if counter() == "add1":
                            attempts_counter += 1
                            continue
                        else:
                            sys.exit(0)
                break

            elif re.search("^(\s)*[Qq](\s)*$",inp_stats_choice):
                print("As you wish. Goodbye!")
                sys.exit(0)

            else:
                if counter() == "add1":
                    attempts_counter += 1
                    continue
                else:
                    sys.exit(0)
        break
    elif re.search("^(\s)*[Nn](\s)*$",inp_see_stats):
        print("OK, maybe next time then.\nGoodbye.")
        sys.exit(0)

    elif re.search("^(\s)*[NnQq](\s)*$",inp_see_stats):
        print("Goodbye")
        sys.exit(0)

    else:
        if counter() == "add1":
            attempts_counter += 1
            continue
        else:
            sys.exit(0)
