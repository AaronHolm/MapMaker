import folium
import sqlalchemy as sa
import pandas as pd
import geopandas as geo
from io import StringIO
from os import listdir
from os.path import isfile, join
from config import SQL_ADDRESS
from selenium import webdriver

import time


#red_icon_path = r"/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_red.png"
#blue_icon_path = r"/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_light_blue.png"
#green_icon_path = r"/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_green.png"


#win_dir = "C:/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_green.png"
#win_dir = "C:/Users/AHolm/Work Folders/Documents/codebin/Mapmaker/html/"
win_dir = "C:/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/Projects/"
linux_dir = '/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/Projects/'
#chromedriver_loc = '/mnt/c/Users/Aaron/Documents/codebin/chromedriver_win32/chromedriver.exe'
#chromedriver_loc = '/mnt/c/Users/AHolm/Work Folders/Documents/OLD Appdata/OneDrive - SEIA/codebin/scrapers/chromedriver_win35/chromedriver.exe'
chromedriver_loc = '/mnt/c/Users/AHolm/Work Folders/Documents/codebin/chromedriver_win32/chromedriver.exe'

def get_cd116():
  engine = sa.create_engine(SQL_ADDRESS)
  query = 'select * from tiger.congress_us_116'
  #df = pd.read_sql(query, engine)
  df = geo.GeoDataFrame.from_postgis(query, engine, geom_col='geom')
  df['state_fips_int'] = df['statefp'].astype(int)
  states = pd.read_sql('select * from reference.states_fips', engine)
  df = df.merge(states, how='left', left_on='state_fips_int', right_on='fips_code')
  df['is_district'] = 1
  df['district'] = [str(row['state_abbr']) + '-' + str(row['cd116fp']) for i, row in df.iterrows()]
  #output = StringIO()
  #df.to_file(output, driver="GeoJSON")
  #print(df.head())
  #print(output)

  query = '''select *
             from projects.projects
             where cd116 is not null and 
                   lat is not null and 
                   lon is not null and 
                   capacity_seia_mw is not null and 
                   status_main in ('Operating', 'Under Construction', 'Under Development');'''

  projs = pd.read_sql(query, engine)
  projs.loc[:, 'cd116'] = [x.split('-')[0] + '-0' + x.split('-')[1] if len(x) == 4 else x for x in projs['cd116']]
  #df = df[df['district'].isin(nsd['cd116'].unique().tolist())]
  return df, projs

def create_map():
  # Get the district shapefile and the list of projects that have already been spatially joined to the appropriate congressional district
  geo_df, projs = get_cd116()


  # Loop through each district shape
  # and use the district name to filter the list of projects
  # to build a map of projects in that district;
  for i, row in geo_df.iterrows():
  #for i, row in nsd.iterrows():
    marker_array = []
    tmp_df = geo_df[geo_df['district'] == row['district']]
    tmp_projs = projs[projs['cd116'] == row['district']]
    print(tmp_projs.head())
    # Hawaii's get bounds function is far too wide/large for the state or district, so set bound explicitly
    # This is not a great way to do this, but works as a first step.
    # Next step would be to build a dictionary of these bounds that can be filtered by district
    # Would need to examine each of the districts, perhaps exporting each of the bounds temporarily
    # in the code below to build a base version
    if(row['district'] == 'HI-02'):
      x1 = -160.678701
      y1 = 18.927830
      x2 = -154.724111
      y2 = 22.360977
    else:
      x1, y1, x2, y2 = tmp_df['geom'].iloc[0].bounds
    print(f"x1: {x1}  y1: {y1}    x2: {x2}  y2: {y2}")
    # For the base map, use the Mapbox api to access our typical styled tiles
    map = folium.Map(location=[45.5236, -122.6750], 
                     tiles="https://api.mapbox.com/styles/v1/aaronleeh/cjr11cc8j1r602sp26k42ckh9/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoiYWFyb25sZWVoIiwiYSI6IjF0SjNqUUUifQ.0sVfP4L9LWoycJoinMovtA",
                     #API_key='pk.eyJ1IjoiYWFyb25sZWVoIiwiYSI6IjF0SjNqUUUifQ.0sVfP4L9LWoycJoinMovtA',
                     attr="SEIA",
                     zoom_control=False)
    # Color the district shape to provide a visual reference of the geography
    folium.Choropleth(geo_str=tmp_df,
                   fill_color='#ffe148',
                   fill_opacity=0.7,
                   geo_data=tmp_df,
                   line_opacity=1,
                   line_color="#ffe148").add_to(map)
    # Loop through the project data and assign the color and radius based on
    # the project's status for fill color and capacity for circle radius
    for i, prow in tmp_projs.iterrows():
      marker = makeMarker(prow['status_main'], prow['capacity_seia_mw'], [prow['lat'], prow['lon']])
      marker.add_to(map)
      marker_array.append(marker)
    legend = getLegend()
    map.get_root().html.add_child(folium.Element(legend))
    #map.get_root().html.add_child(folium.Element(legendCSS()))

    map.fit_bounds([[y1, x1], [y2, x2]])
    map.save(linux_dir + f"html/{row['district']}.html")
  return

def legendCSS():
  style = '''<style>.legend {background-color: rgba(255,255,255, 0.85);  border-radius: 3px;bottom: 35px;box-shadow: 0 1px 2px rgba(0,0,0,0.10);font: 12px 'Roboto Black', Arial, Helvetica, sans-serif;padding: 10px;position: absolute;left: 10px;z-index: 1; }
    .legend h4 {margin: 0 0 10px; font: 16px 'Roboto Black';}
    .legend div span {border-radius: 50%;display: inline-block;height: 10px;margin-right: 5px;width: 10px;}</style>'''
  return style


def makeMarker(status, capacity, loc):
  colors = {'Operating': 'rgb(136,181,81,1)',
            'Under Construction': 'rgb(47,112,175, 1)',
            'Under Development': 'rgb(240,245,248,1)'}
  color = colors[status]

  print(f"Capacity: {capacity}")
  radius = 7.5
  if(capacity <= 1):
    radius = 7.5
  elif(capacity <= 5):
    radius = 10
  elif(capacity <= 10):
    radis = 15
  elif(capacity <= 25):
    radius = 20
  elif(capacity <= 100):
    radius = 25
  elif(capacity <= 1000):
    radius = 30
  else:
    radius = 7.5

  if(radius):
    print(f"Radius: {radius}")
  else:
    print("Radius is null")

  marker = folium.CircleMarker(location=loc,
                               radius=radius,
                               color=color,
                               weight=1.5,
                               fill=True,
                               fill_color=color)
  return marker

def getLegend():
  legend_html = '''<div style="background-color: rgba(255,255,255, 0.85); border-radius: 3px; bottom: 25px; left: 25px; box-shadow: 0 1px 2px rgba(0,0,0,0.10); font: 12px 'Roboto Black', Arial, Helvetica, sans-serif; padding: 10px; position: fixed; z-index: 1000;">
                      <span style="padding: 4px; background-color:#1f1446;color:#f0f5f8;">Solar Project Database</span>
                                <div><span style="background-color: rgba(255,225,79,1); border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>PV - Operating</div>
				<div><span style="background-color: rgba(247,130,55,1); border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>PV - Under Development</div>
				<div><span style="background-color: rgba(299, 28, 56, 1); border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>PV - Under Construction</div>
				<hr>
				<div><span style="background-color: rgba(59, 179, 229, 100); border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>CSP - Operating</div>
				<div><span style="background-color: rgba(47, 112, 175, 100); border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>CSP - Under Development</div>
				<div><span style="background-color: rgba(31, 20, 70, 100); border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>CSP - Under Construction</div>
				<hr>
				<div style="text-align:center;">Project Capacity</div>
				<div style="text-align: center;">
					<span style="background-color: rgba(255, 225, 255, .25); border-style: solid; border-color: #111; border-width:1px; width: 7.5px; height:7.5px;margin:0 30 px; border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>
					<span style="background-color: rgba(255, 255, 255, .25); border-style: solid; border-color: #111; border-width:1px; width: 10px; height:10px;margin:0 30 px; border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>
					<span style="background-color: rgba(255, 255, 255, .25); border-style: solid; border-color: #111; border-width:1px; width: 15px; height:15px;margin:0 30 px; border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>
					<span style="background-color: rgba(255,255,255,.25); border-style: solid; border-color: #111; border-width:1px;  width: 20px; height:20px;margin:0 30 px; border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>
					<span style="background-color: rgba(255,255,255,.25);  border-style: solid; border-color: #111; border-width:1px; width: 25px; height:25px;margin:0 30 px; border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span>
					<span style="background-color: rgba(255,255,255,.25);  border-style: solid; border-color: #111; border-width:1px; width: 30px; height:30px;margin:0 30 px; border-radius: 50%; display: inline-block; height: 10px; margin-right: 5px; width: 10px;"></span></div>
				<div style="text-align:center;">1     -     100+ MW</div>
			</div>
                    </div>'''
  return legend_html

def convert_to_image():
  options = {"xvfb":"", 
             "format":'png', 
             "encoding":"UTF-8",
             "height": 1000,
             "width": 1000}
  #dir = '/mnt/c/Users/Aaron/Documents/codebin/Mapmaker/'
  files = [f for f in listdir(linux_dir+'html') if isfile(join(linux_dir, 'html/', f))]
  for f in files:
    imgkit.from_file(linux_dir+'html/'+f, linux_dir+'images/'+f.split('.')[0]+'.png', options=options)
  return

def selenium_image():
  #dir = "/mnt/c/Users/Aaron/Documents/codebin/Mapmaker/"
  #win_dir = "C:/Users/Aaron/Documents/codebin/Mapmaker/html/"
  files = [f for f in listdir(linux_dir+'html') if isfile(join(linux_dir, 'html/', f))]
  #files = [f for f in files if ('HI-01' in f) | ('HI-02' in f)]
  #driver = webdriver.Chrome('/mnt/c/Users/Aaron/Documents/codebin/chromedriver_win32/chromedriver.exe')
  driver = webdriver.Chrome(chromedriver_loc)
  driver.set_window_size(1100,560)
  for f in files:
    #print(dir+'html/'+f)
    driver.get("file:///"+win_dir+'html/'+f)
    time.sleep(2)
    driver.save_screenshot(linux_dir+'images/'+f.split('.')[0]+'.png')
  return


if __name__ == '__main__':
  create_map()
  selenium_image()
  #convert_to_image()
