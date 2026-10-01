import os, requests
import pprint

from datetime import datetime
from .params_models import CalculatorParams, LocationCoordinatesParams, WeatherParams, CurrentDateTimeParams
from .registry import register_tool
from langchain_community.document_loaders import WebBaseLoader

OPEN_WEATHER_API_KEY = os.getenv("OPEN_WEATHER_API_KEY")

@register_tool
def calculator(params: CalculatorParams) -> str:
    """Evaluate a mathematical expression provided in the params."""
    result = eval(params.expression)
    return f"The result of {params.expression} is {result}"

@register_tool
def get_current_date_time(params: CurrentDateTimeParams) -> str:
    """Return the current date and time."""
    now = datetime.now()
    return f"Current date and time: {now.strftime("%Y-%m-%d %H:%M:%S")}"

@register_tool
def get_location_coordinates(params: LocationCoordinatesParams) -> str:
    """Return the geographic coordinates for a given location."""
    api_key = OPEN_WEATHER_API_KEY
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={params.location_name}&limit=1&appid={api_key}"

    try:
        response = requests.get(url)
    except requests.Timeout:
        return f"Error fetching coordinates for '{params.location_name}': Request timed out."
    except Exception as e:
        return f"An error occurred while fetching coordinates for '{params.location_name}': {e}"

    if response.status_code == 404:
        return f"Location '{params.location_name}' not found."
    if response.status_code != 200:
        return f"Error fetching coordinates: {response.status_code} - {response.text}"

    data = response.json()
    pprint.pprint(data)  # Debug: afișează datele brute pentru verificare
    if not data:
        return f"Location '{params.location_name}' not found."
    lat = data[0]["lat"]
    lon = data[0]["lon"]
    return f"Coordinates for '{params.location_name}': Latitude {lat}, Longitude {lon}"

@register_tool
def get_current_weather(params: WeatherParams) -> str:
    """Return the current weather for a given location."""
    api_key = OPEN_WEATHER_API_KEY
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={params.latitude}&lon={params.longitude}&appid={api_key}&units={params.metrics}"
    
    try:
        response = requests.get(url)
    except requests.Timeout:
        return f"Request timed out while fetching weather data for '{params.latitude}, {params.longitude}'."
    except Exception as e:
        return f"An error occurred while fetching weather data for '{params.latitude}, {params.longitude}': {e}"
    
    if response.status_code == 404:
        return f"Weather data not found for coordinates: Latitude {params.latitude}, Longitude {params.longitude}."
    if response.status_code != 200:
        return f"Error fetching weather data: {response.status_code} - {response.text}"

    data = response.json()
    pprint.pprint(data)  # Debug: afișează datele brute pentru verificare
    if data.get("cod") != 200:
        return f"Error fetching weather data: {data.get('message', 'Unknown')}"
    temp = data["main"]["temp"]
    max_temp = data["main"]["temp_max"]
    min_temp = data["main"]["temp_min"]
    description = data["weather"][0]["description"]
    return f"Current weather: {temp}°C, {description}, Max: {max_temp}°C, Min: {min_temp}°C"

    """Return the content of web pages for a given URL list. Use in relation to the get_web_search_results tool."""
    urls = params.urls
    try:
        loader = WebBaseLoader(urls)
        docs = loader.load()

        contents = []
        for doc in docs:
            content = doc.page_content.strip()
            if content:
                contents.append(content)

        return "\n".join(contents)
    except Exception as e:
        return f"Error loading content from URLs: {e}"