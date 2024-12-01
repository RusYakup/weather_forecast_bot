from datetime import timedelta

import aiohttp
import requests
import sys

from pydantic import ValidationError
from telebot.async_telebot import AsyncTeleBot
import logging
import traceback
from typing import Any, Dict

from helpers.model_message import Message
from helpers.models_weather import DayDetails, WeatherData
from prometheus.couters import (count_user_errors, instance_id,
                                count_instance_errors, external_api_error, validation_error)

log = logging.getLogger(__name__)


def check_bot_token(token: str) -> None:
    """
    A function to check the validity of a Telegram bot token by making a request to the Telegram API.

    Parameters:
        token (object): 
    token (str): The token of the Telegram bot to be checked.

    Returns:
    None
    """
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url)
        response.raise_for_status()
        info = response.json()
        log.info("Token for Telegram bot verified: " + info['result']['username'])
    except requests.exceptions.RequestException as e:
        log.critical("Error verifying Telegram bot token %s", token)
        log.debug(f"Exception verifying Telegram bot token: {e}")
        sys.exit(1)


def check_api_key(api_key: str) -> None:
    """
    A function to check the validity of an API key by making a request to a weather API.

    Parameters:
    - api_key (str): The API key to be checked.

    Returns:
    - None
    """
    url = f'http://api.weatherapi.com/v1/current.json?key={api_key}&q=Kazan'
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.critical("Error verifying API key")
        log.debug(f"Exception: {e}")
        sys.exit(1)
    response = requests.get(url)
    if response.status_code == 200:
        log.info("The API key is correct.")
    else:
        log.critical("Error verifying API key: Status code " + str(response.status_code))
        log.debug(F"Exception traceback:\n", traceback.format_exc())
        sys.exit(1)


def wind(win_dir: str, wind_kph: float, max_wind_kph: float) -> str:
    """
        1) translates wind direction from English to Russian
        2) converts wind speed km/h to m/s
        Args:
        win_dir (str): The direction of the wind in English.
        wind_kph (float): The speed of the wind in kilometers per hour.
        max_wind_kph (float): The maximum speed of the wind in kilometers per hour.
        Returns:
        str: Sentence indicating wind direction, m/s speed and maximum wind speed on that day
        """
    #
    direction = {
        'N': "Северный",
        'NNE': "Северо-северо-восточный",
        'NE': "Северо восточный",
        'ENE': "Восточно-северо-восточный",
        'E': "Восточный",
        'ESE': "Восточно-юго-восточный",
        'SE': "Северный юго-восточный",
        'SSE': "Юго-юго-восточный",
        'S': "Южный",
        'SSW': "Юго-юго-западный",
        'SW': "Юго западный",
        'WSW': "Западно-юго-западный",
        'W': "Западный",
        'WNW': "Западно-северо-западный",
        'NW': "Северный западный",
        'NNW': "Северо-северо-западный"
    }
    wind_ms = round(wind_kph / 3.6)
    max_wind_ms = round(max_wind_kph / 3.6)
    if win_dir in direction:
        return f"Wind {win_dir} {wind_ms} m/s (with maximum wind speed of {max_wind_ms} m/s)"
    else:
        log.debug("Wind direction is unknown.")
        return "Wind direction is unknown."


def weather_condition(precipitation: str) -> str:
    weather_dict = {
        "Sunny": "Солнечно",
        "Partly cloudy": "Переменная облачность",
        "Cloudy": "Облачно",
        "Overcast": "Пасмурная погода",
        "Mist": "Туман",
        "Patchy rain possible": "Возможен кратковременный дождь",
        "Patchy snow possible": "Возможен кратковременный снег",
        "Patchy sleet possible": "Возможен кратковременный мокрый снег",
        "Patchy freezing drizzle possible": "Возможен кратковременный ледяной дождь",
        "Thundery outbreaks possible": "Возможны грозовые вспышки",
        "Blowing Snow": "Низовая метель",
        "Blizzard": "Метель",
        "Fog": "Туман",
        "Freezing fog": "Ледяной туман",
        "Patchy light drizzle": "Небольшой мелкий дождь",
        "Light drizzle": "Легкая морось",
        "Freezing drizzle": "Изморозь",
        "Heavy freezing drizzle": "Сильный ледяной дождь",
        "Patchy light rain": "Небольшой дождь",
        "Light rain": "Легкий дождь",
        "Moderate rain at times": "Временами умеренный дождь",
        "Moderate rain": "Умеренный дождь",
        "Heavy rain at times": "Временами сильный дождь",
        "Heavy rain": "Ливень",
        "Light freezing rain": "Легкий ледяной дождь",
        "Moderate or heavy freezing rain": "Умеренный или сильный ледяной дождь",
        "Light sleet": "Легкий мокрый снег",
        "Moderate or heavy sleet": "Умеренный или сильный мокрый снег",
        "Patchy light snow": "Небольшой мелкий снег",
        "Light snow": "Легкий снег",
        "Patchy moderate snow": "Неровный умеренный снег",
        "Moderate snow": "Умеренный снег",
        "Patchy heavy snow": "Неровный сильный снег",
        "Heavy snow": "Сильный снегопад",
        "Ice pellets": "Ледяная крупа",
        "Light rain shower": "Небольшой дождь моросит",
        "Moderate or heavy rain shower": "Умеренный или сильный ливень",
        "Torrential rain shower": "Проливной ливень",
        "Light sleet showers": "Небольшой ливень с мокрым снегом",
        "Moderate or heavy sleet showers": "Умеренный или сильный ливень с мокрым снегом",
        "Light snow showers": "Легкий снегопад",
        "Moderate or heavy snow showers": "Умеренный или сильный снегопад",
        "Light showers of ice pellets": "Легкий дождь ледяных крупинок",
        "Moderate or heavy showers of ice pellets": "Умеренные или сильные ливни ледяной крупы",
        "Patchy light rain with thunder": "Небольшой дождь с грозой",
        "Moderate or heavy rain with thunder": "Умеренный или сильный дождь с грозой",
        "Patchy light snow with thunder": "Небольшой снег с грозой",
        "Moderate or heavy snow with thunder": "Умеренный или сильный снег с грозой",
        "Patchy rain nearby": "Возможен кратковременный дождь",
    }
    if precipitation.capitalize() in weather_dict:
        return weather_dict[precipitation]
    else:
        log.error(f"Unknown precipitation: {precipitation}")
        return precipitation


async def get_response(message: Message, api_url: str, bot: AsyncTeleBot) -> Dict[str, Any]:
    """
    A function to make a GET request to the provided API URL and handle different response status codes.

    Parameters:
    - message: The message object to send responses to.
    - api_url: The URL of the API to make the GET request to.
    - bot: An AsyncTeleBot object to interact with Telegram for sending messages.

    Returns:
    - Any: The JSON response from the API if the status code is 200, otherwise appropriate error messages are sent to the user.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json(content_type=None)
                if response.status == 200:
                    logging.debug("Response 200")
                    return data
                elif response.status == 400:
                    error_code = data.get('error', {}).get('code')
                    if error_code == 1005:
                        logging.error(
                            f"Invalid API request URL - Response 400: code 1005 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id, "Invalid API request URL. Please try again later.")
                    elif error_code == 1006:
                        count_user_errors.labels(instance=instance_id).inc()
                        logging.error(
                            f"City not found - Response 400: code 1006 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id, "City not found, please check the city name.")
                    elif error_code == 9999:
                        logging.error(
                            f"Internal application error - Response 400: code 9999 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id, "Internal application error. Please try again later.")
                    else:
                        logging.error(f"Unknown error - Response 400 code {data.get('error', {}).get('message')}")
                        logging.debug(f"Exception traceback: \n {traceback.format_exc()}")
                        await bot.send_message(message.chat.id, "Unknown error. Please try again later.")

                elif response.status == 401:
                    external_api_error.labels(instance=instance_id, status_code=response.status).inc()
                    error_code = data.get('error', {}).get('code')
                    if error_code == 1002:
                        logging.error(
                            f"API key not provided - Response 401: code 1002 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id, "API key not provided. Please contact support.")
                    elif error_code == 2006:
                        logging.error(
                            f"Invalid API key - Response 401: code 2006 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id,
                                               "The provided API key is invalid. Please contact support.")
                elif response.status == 403:
                    external_api_error.labels(instance=instance_id, status_code=response.status).inc()
                    error_code = data.get('error', {}).get('code')
                    if error_code == 2007:
                        logging.error(
                            f"API key exceeded monthly call quota - Response 403: code 2007 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id,
                                               "API key has exceeded the monthly call quota. Please contact support.")
                    elif error_code == 2008:
                        logging.error(
                            f"API key disabled - Response 403: code 2008 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id, "API key is disabled. Please contact support.")
                    elif error_code == 2009:
                        logging.error(
                            f"API key does not have access - Response 403: code 2009 {data.get('error', {}).get('message')}")
                        await bot.send_message(message.chat.id,
                                               "API key does not have access to the requested resource. Please contact support.")
                elif response.status == 404:
                    logging.error("Response 404: Not found")

                    await bot.send_message(message.chat.id,
                                           "Requested resource not found, please try again later or contact support.")
                elif response.status == 500:
                    logging.error("Response 500: Internal server error")
                    await bot.send_message(message.chat.id, "Internal server error. Please try again later.")
                elif response.status == 502:
                    logging.error("Response 502: Bad gateway")
                    await bot.send_message(message.chat.id, "Bad gateway error. Please try again later.")
                else:
                    logging.error(f"Response {response.status}: {data.get('error', {}).get('message')}")
                    await bot.send_message(message.chat.id, "Error retrieving weather data, please try again later.")
    except Exception as e:
        count_instance_errors.labels(instance=instance_id).inc()
        logging.error(f"Error in get_response: {str(e)}")
        logging.debug(f"Exception:\n {traceback.format_exc()}")
        await bot.send_message(message.chat.id, "An error occurred")


async def calculate_avg_temp_7days(message, today_date, status_user, config, bot):
    avgtemp_c_7days = set()
    try:
        for days in range(1, 8):
            statistic_date = today_date - timedelta(days=days)
            url_prediction = f'https://api.weatherapi.com/v1/history.json?key={config.API_KEY}&q={status_user["city"]}&dt={statistic_date}'
            data = await get_response(message, url_prediction, bot)
            day_details = DayDetails.model_validate(data['forecast']['forecastday'][0]['day'])
            avgtemp_c_7days.add(day_details.avgtemp_c)
    except ValidationError as e:
        validation_error.labels(instance=instance_id).inc(0)
        await bot.send_message(message.chat.id, f"Error")
        log.error(f"prediction: Validation error {e}")
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
    return round(sum(avgtemp_c_7days) / len(avgtemp_c_7days))


async def calculate_avg_temp_3days(message, status_user, config, bot):
    avgtemp_c_3days = set()
    for days in range(3):
        url_forecast_several = f'http://api.weatherapi.com/v1/forecast.json?key={config.API_KEY}&q={status_user["city"]}&days=3&aqi=no&alerts=no'
        data = await get_response(message, url_forecast_several, bot)
        for day_num in range(1, len(data['forecast']['forecastday'])):
            weather_data = WeatherData.model_validate(data)
            forecast_data = weather_data.forecast.forecastday[day_num]
            avgtemp_c_3days.add(forecast_data.day.avgtemp_c)
    return round(sum(avgtemp_c_3days) / len(avgtemp_c_3days))


def logging_config(log_level: str) -> None:
    """
    A function that configures logging based on the input log level.

    :param log_level: The log level to set for the logging configuration.
    :return: None
    """
    numeric_level = getattr(logging, log_level.upper())
    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log.info("Logging Configured")
