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


red_icon_path = r"/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_red.png"
blue_icon_path = r"/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_light_blue.png"
green_icon_path = r"/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_green.png"


#win_dir = "C:/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_green.png"
#win_dir = "C:/Users/AHolm/Work Folders/Documents/codebin/Mapmaker/html/"
win_dir = "C:/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/"
linux_dir = '/mnt/c/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/'
#chromedriver_loc = '/mnt/c/Users/Aaron/Documents/codebin/chromedriver_win32/chromedriver.exe'
chromedriver_loc = '/mnt/c/Users/AHolm/Work Folders/Documents/OLD Appdata/OneDrive - SEIA/codebin/scrapers/chromedriver_win35/chromedriver.exe'

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
             from markets.nsd_clean2 
             where cd116 is not null and 
                   "Primary Category" not in ('Government', 'Corporate Solar User', 'Electrical Utility', 'Educational Institution', 'Oil & Gas', 'Partnership', 'Sponsorship', 'None') and 
                   "Solar" = 'True';'''
  nsd = pd.read_sql(query, engine)
  #df = df[df['district'].isin(nsd['cd116'].unique().tolist())]
  return df, nsd

def create_map():
  #print(folium.__version__)
  #get_cd116()
  geo_df, nsd = get_cd116()


  #geo_df = geo_df[geo_df['district'].isin(['HI-02', 'HI-01'])]
  for i, row in geo_df.iterrows():
  #for i, row in nsd.iterrows():
    marker_array = []
    tmp_df = geo_df[geo_df['district'] == row['district']]
    tmp_nsd = nsd[nsd['Congressional District'] == row['district']]
    print(tmp_nsd.head())
    if(row['district'] == 'HI-02'):
      x1 = -160.678701
      y1 = 18.927830
      x2 = -154.724111
      y2 = 22.360977
    else:
      x1, y1, x2, y2 = tmp_df['geom'].iloc[0].bounds
    print(f"x1: {x1}  y1: {y1}    x2: {x2}  y2: {y2}")
    map = folium.Map(location=[45.5236, -122.6750], 
                     tiles="https://api.mapbox.com/styles/v1/aaronleeh/cjr11cc8j1r602sp26k42ckh9/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoiYWFyb25sZWVoIiwiYSI6IjF0SjNqUUUifQ.0sVfP4L9LWoycJoinMovtA",
                     #API_key='pk.eyJ1IjoiYWFyb25sZWVoIiwiYSI6IjF0SjNqUUUifQ.0sVfP4L9LWoycJoinMovtA',
                     attr="SEIA",
                     zoom_control=False)
    folium.Choropleth(geo_str=tmp_df,
                   fill_color='#2f70af',
                   fill_opacity=0.25,
                   geo_data=tmp_df,
                   line_opacity=0).add_to(map)
    for i, nrow in tmp_nsd.iterrows():
      if(nrow['Primary Category'] == 'Manufacturer/Supplier'):
        #color = 'red'
        icon_path = red_icon_path
      elif(nrow['Primary Category'] == 'Contractor/Installer'):
        #color = 'blue'
        icon_path = blue_icon_path
      else:
        #color = 'green'
        icon_path = green_icon_path
      #icon_path = r"C:/Users/Aaron/Documents/codebin/Mapmaker/maki/icons/marker-stroked-11.svg"
      #icon_path = r"/mnt/c/Users/Aaron/Documents/codebin/Mapmaker/maki/icons/marker-stroked-11.png"
      #icon_path = r"/mnt/c/Users/Aaron/Documents/codebin/Mapmaker/maki/icons/icons8-marker-40.png"

      icon = folium.features.CustomIcon(icon_image=icon_path, icon_size=(20,20))

      #folium.Marker([nrow['lat'], nrow['lon']], icon=folium.Icon(color=color)).add_to(map)
      #folium.Marker([nrow['lat'], nrow['lon']], icon=icon).add_to(map)
      marker = folium.Marker([nrow['lat'], nrow['lon']], icon=icon)
      marker.add_to(map)
      marker_array.append(marker)
    legend = getLegend()
    map.get_root().html.add_child(folium.Element(legend))
    
    map.fit_bounds([[y1, x1], [y2, x2]])
    map.save(linux_dir + f"html/{row['district']}.html")
    #map.save(f"/mnt/c/Users/Aaron/Documents/codebin/Mapmaker/images/{row['district']}_map.png")

  #x1, y1, x2, y2 = geo_df['geom'].iloc[0].bounds
  #map.choropleth(geo_str=geo_df, 
  #               fill_color="#37b3e5", 
  #               fill_opacity=0.5, 
  #               geo_data=geo_df, 
  #               line_opacity=0)
  
  #map.fit_bounds([[bb[0], bb[1]], [bb[2], bb[3]]])
  #map.fit_bounds([[y1, x1], [y2, x2]])
  #map.save('/mnt/c/Users/Aaron/Documents/codebin/Mapmaker/map.html')
  return

def getLegend():
  #legend_html = '''<div style="position: fixed; bottom: 50px; left: 50px; border: 2px solid grey; z-index: 9999; font-size: 14px; background-color:#f0f5f8;">
  #                  <span style="background-color:#1f1446;color:#f0f5f8;">National Solar Database</span><br>
  #                  &nbsp;Manufacturer &nbsp; <i class="fa fa-map-marker fa-2x" style="color:red; float:right;"></i><br>
  #                  &nbsp;Installer &nbsp; <i class="fa fa-map-marker fa-2x" style="color:blue; float:right;"></i><br>
  #                  &nbsp;Other &nbsp; <i class="fa fa-map-marker fa-2x" style="color:green; float:right;"></i><br>
  #                  </div>'''
  legend_html = '''<div style="position: fixed; bottom: 25px; left: 25px; z-index: 9999; font-size: 14px; background-color:#f0f5f8;">
                      <span style="padding: 4px; background-color:#1f1446;color:#f0f5f8;">National Solar Database</span>
                      <div>
                        <p style="display: flex; padding-left: 5px; padding-top: 5px; align-items: center; justify-content: space-between; height: 15px;">Manufacturer<img src="C:/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_red.png" style="height:11px; width: 11px; float:right;"></img></p>
                        <p style="display: flex; padding-left: 5px; align-items: center; justify-content: space-between; height: 15px;">Installer<img src="C:/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_light_blue.png" style="height: 11px; width: 11px; float:right;"></img></p>
                        <p style="display: flex; padding-left: 5px; align-items: center; justify-content: space-between; height: 15px;">Other<img src="C:/Users/AHolm/Work Folders/Documents/SMI/Factsheets/Maps/marker-11_green.png" style="height: 11px; width: 11px; float:right;"></img></p>
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
