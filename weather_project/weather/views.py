from django.shortcuts import render
import requests

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

import os


def index(request):
    city = request.GET.get('city')
    state = request.GET.get('state')

    currentWeather = None
    forecast = None
    error = None


    if (not city) or (not state):
        error = 'Please enter a city and state.'
    else:
        latitude, longitude = getCoordinates(city, state)
        if (not latitude) or (not longitude):
            error = "Could not find the specified location."
             
            return render(request, 'weather/index.html', {
            'city' : city,
            'state' : state,
            'current_weather' : currentWeather,
            'forecast' : forecast,
            'error' : error
            })
     
     
        #------------- Copy/pasted from open-meteo's API response -------------#

        # Setup the Open-Meteo API client with cache and retry on error
        cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
        retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
        openmeteo = openmeteo_requests.Client(session = retry_session)

        # Make sure all required weather variables are listed here
        # The order of variables in hourly or daily is important to assign them correctly below
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
            "current": ["temperature_2m", "weather_code", "apparent_temperature"],
            "temperature_unit": "fahrenheit",
        }
        responses = openmeteo.weather_api(url, params = params)

        # Process first location. Add a for-loop for multiple locations or weather models
        response = responses[0]

        print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation: {response.Elevation()} m asl")
        print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

        # Process current data. The order of variables needs to be the same as requested.
        current = response.Current()
        current_temperature_2m = current.Variables(0).Value()
        current_weather_code = current.Variables(1).Value()
        current_apparent_temperature = current.Variables(2).Value()

        print(f"\nCurrent time: {current.Time()}")
        print(f"Current temperature_2m: {current_temperature_2m}")
        print(f"Current weather_code: {current_weather_code}")
        print(f"Current apparent_temperature: {current_apparent_temperature}")

        # Process daily data. The order of variables needs to be the same as requested.
        daily = response.Daily()
        daily_weather_code = daily.Variables(0).ValuesAsNumpy()
        daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()
        daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()

        daily_data = {"date": pd.date_range(
            start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
            end =  pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = daily.Interval()),
            inclusive = "left"
        )}

        daily_data["weather_code"] = daily_weather_code
        daily_data["temperature_2m_max"] = daily_temperature_2m_max
        daily_data["temperature_2m_min"] = daily_temperature_2m_min

        daily_dataframe = pd.DataFrame(data = daily_data)
        print("\nDaily data\n", daily_dataframe)

        #------------- End copy/paste -------------#

        # Current weather formatting
        currentWeather = {
             'date' : current.Time,
             'temperature' : round(current_temperature_2m),
             'condition' : parseWeatherCode(current_weather_code),
             'icon' : getWeatherIcon(current_weather_code),
        }
        
        # Forecast formatting
        forecast = []

        for i in range(5):
             forecast.append({
                  'date' : daily_data['date'][i],
                  'condition': parseWeatherCode(daily_data['weather_code'][i]),
                  'high' : round(daily_data['temperature_2m_max'][i]),
                  'low' : round(daily_data['temperature_2m_min'][i]),
                  'icon' : getWeatherIcon(daily_data['weather_code'][i]),
             })

        if (city and state):
            city = city.capitalize()
            state = state.capitalize()

    return render(request, 'weather/index.html', {
        'city' : city,
        'state' : state,
        'currentWeather' : currentWeather,
        'forecast' : forecast,
        'error' : error
    })


# Coordinate data derived from a csv provided by simplemaps.com:
# https://simplemaps.com/data/us-cities
def getCoordinates(city, state):

        city, state = capitalizeInput(city, state)

        BASE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        CSV_PATH = os.path.join(BASE_DIRECTORY, 'weather', 'uscities.csv')

        data = pd.read_csv(CSV_PATH)

        try:   
            filtered = data[(data['city'] == city) & (data['state_name'] == state)]
            longitude = filtered['lat'].values[0]
            latitude = filtered['lng'].values[0]
        except:
             longitude = None
             latitude = None

        return (longitude, latitude)


def capitalizeInput(city, state):
    
    splitCity = city.split()
    splitCity = map(lambda x: x.capitalize(), splitCity) # Capitalizing every word
    city = ' '.join(splitCity)

    splitState = state.split()
    splitState = map(lambda x: x.capitalize(), splitState)
    state = ' '.join(splitState)

    return (city, state)
         
# Open-meteo's documentation provides descriptions for each possible weather code
def parseWeatherCode(code):
     if (code == 0):
          return 'Clear skies'
     elif (code == 1):
          return 'Mainly clear skies'
     elif (code == 2):
          return 'Partly cloudy'
     elif (code == 3):
          return 'Overcast'
     elif (code == 45):
          return 'Foggy'
     elif (code == 48):
          return 'Freezing fog'
     elif (code == 51):
          return 'Light drizzle'
     elif (code == 53):
          return 'Moderate drizzle'
     elif (code == 55):
          return 'Intense drizzle'
     elif (code == 56):
          return 'Light freezing drizzle'
     elif (code == 57):
          return 'Intense freezing drizzle'
     elif (code == 61):
          return 'Slight rain'
     elif (code == 63):
          return 'Moderate rain'
     elif (code == 65):
          return 'Heavy rain'
     elif (code == 66):
          return 'Light freezing rain'
     elif (code == 67):
          return 'Heavy freezing rain'
     elif (code == 71):
          return 'Light snow fall'
     elif (code == 73):
          return 'Moderate snow fall'
     elif (code == 75):
          return 'Heavy snow fall'
     elif (code == 77):
          return 'Snow grains'
     elif (code == 80):
          return 'Light rain showers'
     elif (code == 81):
          return 'Moderate rain showers'
     elif (code == 82):
          return 'Violent rain showers'
     elif (code == 85):
          return 'Light snow showers'
     elif (code == 86):
          return 'Heavy snow showers'
     elif (code == 95):
          return 'Light to moderate thunderstorm'
     elif (code == 96):
          return 'Thunderstorm with hail'
     
     return 'Failed to fetch weather data'


def getWeatherIcon(code):
    if (code == 0):
        return 'weather/icons/sunny.png'
    elif (code == 1):
        return 'weather/icons/partly_cloudy.png'
    elif (code == 2):
        return 'weather/icons/partly_cloudy.png'
    elif (code == 3):
        return 'weather/icons/cloudy.png'
    elif (code == 45):
        return 'weather/icons/foggy.png'
    elif (code == 48):
        return 'weather/icons/light_rain.png'
    elif (code == 51):
        return 'weather/icons/light_rain.png'
    elif (code == 53):
        return 'weather/icons/heavy_rain.png'
    elif (code == 55):
        return 'weather/icons/heavy_rain.png'
    elif (code == 56):
        return 'weather/icons/light_rain.png'
    elif (code == 57):
        return 'weather/icons/heavy_rain.png'
    elif (code == 61):
        return 'weather/icons/light_rain.png'
    elif (code == 63):
        return 'weather/icons/heavy_rain.png'
    elif (code == 65):
        return 'weather/icons/heavy_rain.png'
    elif (code == 66):
        return 'weather/icons/light_rain.png'
    elif (code == 67):
        return 'weather/icons/heavy_rain.png'
    elif (code == 71):
        return 'weather/icons/snowy.png'
    elif (code == 73):
        return 'weather/icons/snowy.png'
    elif (code == 75):
        return 'weather/icons/snowy.png'
    elif (code == 77):
        return 'weather/icons/snowy.png'
    elif (code == 80):
        return 'weather/icons/light_rain.png'
    elif (code == 81):
        return 'weather/icons/heavy_rain.png'
    elif (code == 82):
        return 'weather/icons/heavy_rain.png'
    elif (code == 85):
        return 'weather/icons/snowy.png'
    elif (code == 86):
        return 'weather/icons/snowy.png'
    elif (code == 95):
        return 'weather/icons/storm.png'
    elif (code == 96):
        return 'weather/icons/storm.png'
    
    return 'weather/icons/cloudy.png'
          
     
     
     

     
