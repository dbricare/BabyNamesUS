from flask import Flask, render_template, request, redirect
import numpy as np
import pandas as pd
import operator, os, datetime, json
from bokeh.plotting import figure, output_file, save, show, ColumnDataSource
from bokeh.models import HoverTool, OpenURL, TapTool
from bokeh.resources import CDN
from bokeh.embed import components, autoload_static


app = Flask(__name__)

dfraw = pd.read_csv('NationalNames.csv', sep=',')

# values for populating drop down menus
glist = (('B','Both'), ('F','Female'), ('M','Male'))
poplist = (('1.00','Most popular'), ('0.90', 'Top 10%'), ('0.75', 'Top 25%'), 
            ('0.50','Middle 50%'), ('0.25','Bottom 25%'), ('0.10','Bottom 10%'), 
            ('0.00','Least popular'))

#
# function definitions
#
def stats(gender, popularity, viewsize=20, mincount=1000, 
            earliest=dfraw.Year.min(), latest=dfraw.Year.max()):
    '''
    Operates on globally defined dataframe 'dfraw'
    Data comes from a 44mb CSV stored locally
    '''
    dfrecent = dfraw[(dfraw.Year>=int(earliest)) & (dfraw.Year<=int(latest))]
    
    dfgroup = dfrecent[['Name','Gender','Count']].groupby(['Name','Gender'], 
                        sort=False, as_index=False).sum()
    
    dfreccom = dfgroup[dfgroup.Count>mincount]
    
    if gender == 'M' or gender == 'F':
        df = dfreccom[dfreccom.Gender.values==gender]
    else:
        df = dfreccom
    
    poptarget = df.Count.quantile(popularity)
    dfquant = df.iloc[(df.Count-poptarget).abs().argsort()[:viewsize]]
    dfout = dfquant.sort_values(by='Count',ascending=True, 
                                inplace=False).reset_index(drop=True)
    return dfout


# flask page functions
@app.route('/')
def main():
    return redirect('/index')
    
# @app.route('/postmethod', methods = ['POST'])
# def get_post_javascript_data():
#     jsdata = request.form['javascript_data']
#     return jsdata

@app.route('/index', methods=['GET', 'POST'])
def index(): 
    
    def colors(gender):
        if gender=='M':
            clr = "#57B768"
        elif gender=='F':
            clr = "#A979BE"
        return clr
    
    def calcoffset(right, mx):
        if right < 0.14 * (dfout.Count.max()-mincount):
            txtclr = "black"
            offset = max(right*1.5, right+(0.04*mx))
            align = "left"
        else:
            txtclr = "white"
            offset = min(right*0.9, right-(0.1*mx))
            align = "right"
        return pd.Series([txtclr, offset, align])
    
    # debugging
    script = ''
    div = ''
    
    # get variables
    if request.method=='GET':
        earliest=1980
        latest=2014
        mincount=10000
        viewsize=10
        gender='B'
        popularity=0
    else:
        gender = request.form['gender']
        popularity = float(request.form['popularity'])
        mincount = int(request.form['mincount'])
        viewsize = int(request.form['viewsize'])
        earliest = request.form['earliest']
        latest = request.form['latest']
    
    # process raw data
    dfout = stats(gender, popularity, earliest=earliest, 
                    latest=latest, mincount=mincount, viewsize=viewsize)
    
    # add necessary columns
    dfout['Color']=dfout.Gender.apply(colors)
    dfout['Right']=dfout.Count-mincount
    mx = dfout.Count.max()-mincount
    dfout = pd.concat([dfout,dfout['Right'].apply(lambda x: calcoffset(x, mx))],axis=1)

    # rename columns with string names
    col = dfout.columns.tolist()
    col[-3:] = ['TextColor', 'Offset', 'Align']
    dfout.columns = col

    #
    # generate plot
    #
    output_file("index.html")
    
    source = ColumnDataSource(dfout)

    hover = HoverTool(tooltips=[("Name", "@Name"), ("Total Count", "@Count")], 
                        names=['bars'])

    # save  value for x range max value
    rt = dfout.Count.max()-mincount+1
    p = figure(width=750, height=600, y_range=(0,len(dfout)+1), 
                x_range=(0,rt), tools=[hover, 'reset','save'])

    # plot bars
    p.quad(left=[0]*viewsize, bottom=[x+0.6 for x in range(0,viewsize)], 
            top=[x+1.4 for x in range(0,viewsize)], right=dfout.Right, color=dfout.Color,
            source=source, name='bars')
    
    # add name labels
    p.text(x=dfout.Offset, y=dfout.index+0.8, text=dfout.Name.tolist(), 
            text_color=dfout.TextColor.tolist(), text_align="center", 
            text_font_size="0.8em", text_font="helvetica neue")

    p.xaxis.axis_label = "Number of Babies Above Minimum Count"
    
#     bt = len(dfout)*0.1
#     p.quad(left=0.81*rt, right=0.97*rt, bottom=bt, top=2.7*bt, line_width=1, 
#             line_color="#666666", color="white")
#     p.quad(left=rt*0.83, right=rt*0.86, bottom=bt*1.2, top=bt*1.6, color="#A979BE")
#     p.text(x=0.89*rt, y=1.2*bt, text=["Female"], text_align="left",
#           text_font_size="12px", text_font="helvetica neue", text_color="#666666")
#     p.quad(left=rt*0.83, right=rt*0.86, bottom=bt*2, top=bt*2.45, color="#57B768")
#     p.text(x=0.89*rt, y=2*bt, text=["Male"], text_align="left",
#           text_font_size="12px", text_font="helvetica neue", text_color="#666666")

    p.ygrid.grid_line_color = None
    p.yaxis.major_tick_line_color = None
    p.yaxis.minor_tick_line_color = None
    p.yaxis.major_label_text_color = None

    p.responsive = True

    script, div = components(p)

    # modification date
    t = os.path.getmtime('app.py')
    modt=datetime.date.fromtimestamp(t)
#     updated='{modt:%B} {modt.day}, {modt:%Y}'.format(modt)  
    updated = modt.strftime('%B %d, %Y')

    return render_template('index.html', script=script, div=div, updated=updated, 
                            mincount=mincount, viewsize=viewsize, glist=glist, 
                            poplist=poplist, gcheck=gender,
                            earliest=earliest, latest=latest,
                            pcheck='{:.2f}'.format(popularity))

if __name__ == "__main__":
    app.run(port=33507)
