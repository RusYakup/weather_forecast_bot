from config.config import Settings
from helpers.helpers import wind, get_response, calculate_avg_temp_7days, calculate_avg_temp_3days
from helpers.model_message import Message
from helpers.models_weather import *
from pydantic import ValidationError
from datetime import datetime, date, timedelta
from postgres.database_adapters import sql_update_user_state_bd
import logging
import traceback
from prometheus.couters import count_user_errors, instance_id, count_instance_errors, validation_error
from postgres.decorators import log_database_query
from telebot.async_telebot import AsyncTeleBot
from asyncpg.pool import Pool

log = logging.getLogger(__name__)


async def start_message(message: Message, bot: AsyncTeleBot) -> None:
    """
    Sends a welcome message to the user and initializes their state in the database.
    Args:
        message: Message object containing user information.
        bot: Bot object to send messages.
    Returns:
        None
    """
    try:
        log.info("User %s started bot", message.from_user.first_name)
        msg = (
            f'Hello {message.from_user.first_name}! I am WeatherForecastBot, your personal assistant for getting an accurate'
            f' weather forecast. I can provide you with weather information for any city. Just type the name of the city '
            f'or share your location, and I will tell you what to expect! Shall we begin?'
            f'Here are the commands I know: \n'
            f'/help - help\n'
            f'/change_city - change city\n'
            f'/current_weather - current weather\n'
            f'/weather_forecast - weather forecast for a specific date\n'
            f'/forecast_for_several_days - weather forecast for several days (from 2 to 10)\n'
            f'/weather_statistics - weather statistics for the last 7 days\n'
            f'/prediction - prediction of the average temperature for 3 days\n'
            f'or simply press the menu to display all commands \n')
        await bot.send_message(message.chat.id, msg)
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(traceback.format_exc())
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, 'An error occurred. Please try again later.')


@log_database_query
async def change_city(pool: Pool, message: Message, bot: AsyncTeleBot) -> None:
    """
    Changes the city in the user state based on user input.
    Args:
        pool: The asyncpg Pool.
        message: The message object containing chat information.
        bot: The asynchronous Telegram bot instance.
    """
    try:
        log.debug("User {message.chat.id} wants to change city")
        await bot.send_message(message.chat.id, 'Please enter the new city')
        await sql_update_user_state_bd(bot, pool, message, "city")
        log.debug(f" User {message.chat.id} waiting_value: city")
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(traceback.format_exc())
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, 'An error occurred. Please try again later.')


@log_database_query
async def add_city(pool: Pool, message: Message, bot: AsyncTeleBot, config: Settings) -> None:
    """
    Add a new city to the user's preferences based on the message received.

    Parameters:
    - pool: Database connection pool
    - message: Message object containing the text and chat id
    - bot: Bot object for sending messages
    - config: Configuration object containing API key

    Returns:
    None
    """
    try:
        log.debug("verify city")
        url = f'http://api.weatherapi.com/v1/forecast.json?key={config.API_KEY}&q={message.text}'
        responses = await get_response(message, url, bot)
        if responses:
            await sql_update_user_state_bd(bot, pool, message, "city", message.text)
            log.debug(f"User {message.chat.id} added new city: {message.text}")
            await bot.send_message(message.chat.id, 'City added successfully. Select the next command.')
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, 'An error occurred. Please try again later.')


async def help_message(message: Message, bot: AsyncTeleBot) -> None:
    try:
        log.debug("User requested help")
        help_messages = (
            ('help', 'help'),
            ('change_city', 'change city'),
            ('current_weather', 'current weather'),
            ('weather_forecast', 'weather forecast for a specific date'),
            ('forecast_for_several_days', 'weather forecast for multiple days'),
            ('weather_statistic', 'weather statistics for the last 7 days'),
            ('prediction', 'prediction for 3 days')
        )
        full_msg = '\n'.join([f'/{command} - {description}' for command, description in help_messages])

        await bot.send_message(message.chat.id, full_msg)
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, 'An error occurred. Please try again later.')


async def weather(message: Message, bot: AsyncTeleBot, config: Settings, status_user: dict) -> None:
    """
    Retrieves the current weather data for a specified city and sends a message with the weather information to the user.
    Args:
        message: The message object from the user.
        bot: The bot object for sending messages.
        config: The configuration object containing API_KEY.
        status_user: User status containing the city for weather lookup.
    Returns:
        Log message indicating success or sends an error message to the user.
    """
    try:

        log.info(f"User requested current weather for': {status_user['city']}")
        url_current = f'http://api.weatherapi.com/v1/forecast.json?key={config.API_KEY}&q={status_user["city"]}'
        data = await get_response(message, url_current, bot)
        weather_data = WeatherData.model_validate(data)
        forecast = weather_data.forecast.forecastday[0].day

        city_name = weather_data.location.name
        region = weather_data.location.region
        local_time = weather_data.location.localtime
        temperature = weather_data.current.temp_c
        feels_like = weather_data.current.feelslike_c
        max_temp = forecast.maxtemp_c
        min_temp = forecast.mintemp_c
        wind_info = wind(weather_data.current.wind_dir, weather_data.current.wind_kph,
                         weather_data.forecast.forecastday[0].day.maxwind_kph)
        humidity = weather_data.current.humidity
        precipitation = forecast.daily_chance_of_rain if weather_data.current.temp_c > 0 else forecast.daily_chance_of_snow
        condition = forecast.condition.text

        current_msg = (
            f"{city_name} ({region}): {local_time}\n"
            f"Temperature: {temperature}°C (feels like {feels_like}°C)\n"
            f"Maximum temperature: {max_temp}°C\n"
            f"Minimum temperature: {min_temp}°C\n"
            f"{wind_info}\n"
            f"Humidity: {humidity}% \n"
            f"Precipitation: {precipitation}%\n"
            f"{condition}"
        )

        await bot.send_message(message.chat.id, current_msg)
        return log.info("current_weather: Success")
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, f"Error")
    except ValidationError as e:
        log.error(f"Data validation error {e}")
        validation_error.labels(instance=instance_id).inc(0)
        await bot.send_message(message.chat.id, 'An error occurred. Please try again later.')


async def weather_forecast(pool: Pool, message: Message, bot: AsyncTeleBot) -> None:
    """
    This function sends a message to the user prompting to input a date range,
    updates the database with the date difference, and logs the activity.
    """
    try:
        today_date = date.today()
        max_date = today_date + timedelta(days=10)
        await bot.send_message(message.chat.id,
                               f'Input the date from {today_date} до {max_date}:')
        await sql_update_user_state_bd(bot, pool, message, "date_difference", "waiting_value")

        log.info(f" User {message.chat.id} waiting_value: date_difference")
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, 'An error occurred. Please try again later.')
        return


async def add_day(pool: Pool, message: Message, bot: AsyncTeleBot, config: Settings, status_user: dict) -> None:
    """
    Add a day to the date entered by the user and get the weather forecast for that day if it's within 10 days from today.
    """
    try:
        today_date = date.today()
        input_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        if (input_date - today_date).days <= 10:
            date_difference = (input_date - today_date).days + 2
            await get_weather_forecast(pool, date_difference, message, bot, config, status_user)
        else:
            max_date = today_date + timedelta(days=10)
            await bot.send_message(message.chat.id, f'The entered date must be no later than {max_date}.')
            count_user_errors.labels(instance=instance_id).inc()
            log.debug("add_day: The entered date must be no later than {max_date}.")
    except ValueError:
        await bot.send_message(message.chat.id, "Date must be in the format YYYY-MM-DD.")
        count_user_errors.labels(instance=instance_id).inc()
        log.error("add_day: Does not match the format YYYY-MM-DD.")
    except Exception as e:
        count_instance_errors.labels(instance=instance_id).inc()
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        log.debug(f"User input (weather_forecast): {message.text}")


async def get_weather_forecast(pool: Pool, date_difference: int, message: Message, bot: AsyncTeleBot, config: Settings,
                               status_user: dict) -> None:
    """
    Retrieves weather forecast based on the date difference for the user's city.
    """
    try:
        log.info(
            f"User requested weather forecast {date_difference} days")
        url_forecast = (f'http://api.weatherapi.com/v1/forecast.json?key={config.API_KEY}&'
                        f'q={status_user["city"]}&days={date_difference}&aqi=no&alerts=no')
        data = await get_response(message, url_forecast, bot)
        weather_data = WeatherData.model_validate(data)
        correction_num = int(date_difference) - 2

        forecast_day = weather_data.forecast.forecastday[correction_num]
        max_temp = forecast_day.day.maxtemp_c
        min_temp = forecast_day.day.mintemp_c
        wind_speed = round(forecast_day.day.maxwind_kph / 3.6)
        precipitation = forecast_day.day.daily_chance_of_rain if weather_data.current.temp_c > 0 else \
            weather_data.forecast.forecastday[1].day.daily_chance_of_snow
        condition = forecast_day.day.condition.text

        forecast_msg = (
            f"{weather_data.location.name} ({weather_data.location.region}):{forecast_day.date}\n"
            f"Maximum temperature: {max_temp}°C\n"
            f"Minimum temperature: {min_temp}°C\n"
            f"Wind up to {wind_speed} m/s\n"
            f"Precipitation: {precipitation}%\n"
            f"{condition}")

        await bot.send_message(message.chat.id, forecast_msg)
        await sql_update_user_state_bd(bot, pool, message, "date_difference", "None")
        log.info(f"weather_forecast: Success")
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, f"Error")
    except ValidationError as e:
        validation_error.labels(instance=instance_id).inc(0)
        log.error(f"weather_forecast: Validation error {e}")
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        await bot.send_message(message.chat.id, f"Error data validation, please try again later.")


async def forecast_for_several_days(pool: Pool, message: Message, bot: AsyncTeleBot) -> None:
    """
            A function to send a weather forecast message for several days and update user state with the number of days.
            """
    try:
        await bot.send_message(message.chat.id,
                               f'In this section, you can get the weather forecast for several days.\n'
                               f'Enter the number of days (from 1 to 10):')
        await sql_update_user_state_bd(bot, pool, message, "qty_days")
    except Exception as e:
        log.debug("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        await bot.send_message(message.chat.id, 'An error occurred. Please try again later.')
        count_instance_errors.labels(instance=instance_id).inc()


async def get_forecast_several(message: Message, bot: AsyncTeleBot, config: Settings, status_user: dict) -> None:
    """
    A function to get the weather forecast for several days based on user input.
    """
    try:
        qty_days = int(message.text)
        if 1 <= qty_days <= 10:
            qty_days += 1
        else:
            await bot.send_message(message.chat.id, 'Number of days must be from 1 to 10')
            count_user_errors.labels(instance=instance_id).inc()
            return
    except ValueError:
        await bot.send_message(message.chat.id, f'Invalid input format please try again. {message.text}')
        count_user_errors.labels(instance=instance_id).inc()
        log.error("forecast_for_several_days: Invalid input format" + message.text)
        return
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        count_instance_errors.labels(instance=instance_id).inc()
        return

    url_forecast_several = (f'http://api.weatherapi.com/v1/forecast.json?key={config.API_KEY}&'
                            f'q={status_user["city"]}&days={qty_days}&aqi=no&alerts=no')
    try:
        data = await get_response(message, url_forecast_several, bot)
        weather_data = WeatherData.model_validate(data)
        for day_num in range(1, len(weather_data.forecast.forecastday)):
            forecast = weather_data.forecast.forecastday[day_num]
            date = forecast.date
            max_temp = forecast.day.maxtemp_c
            min_temp = forecast.day.mintemp_c
            wind_speed = round(forecast.day.maxwind_kph / 3.6)
            humidity = forecast.day.avghumidity
            precipitation_probability = forecast.day.daily_chance_of_rain if forecast.day.avgtemp_c > 0 else forecast.day.daily_chance_of_snow
            precipitation_text = forecast.day.condition.text

            msg = (f"{weather_data.location.name} ({weather_data.location.region}):{date}\n"
                   f"Maximum temperature: {max_temp}°C\n"
                   f"Minimum temperature: {min_temp}°C\n"
                   f"Wind up to {wind_speed} m/s\n"
                   f"Humidity: {humidity}% \n"
                   f"Precipitation probability: {precipitation_probability}%\n"
                   f"{precipitation_text}")
            await bot.send_message(message.chat.id, msg)
        log.info(f"several forecast : Success")
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, f"Error requesting data. Please try again later.")
    except ValidationError as e:
        validation_error.labels(instance=instance_id).inc(0)
        log.error(f"forecast_for_several_days: Validation error {e}")
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        await bot.send_message(message.chat.id, f"Error data validation, please try again later.")


async def statistic(message: Message, bot: AsyncTeleBot, config: Settings, status_user: dict) -> None:
    """
    Retrieves and sends weather statistics for a given city for the past week.

    Parameters:
    - message (Message): The message object containing the user's request.
    - bot (AsyncTeleBot): The bot object for sending messages to the user.
    - config (Settings): The application settings configuration.
    - status_user (dict): The status of the user, including the city for which to retrieve weather statistics.

    Returns:
    - None

    Raises:
    - Exception: If an error occurs during the process.
    - ValidationError: If there is a validation error in the received data.

    Notes:
    - This function sends a separate message for each day of the past week, containing the temperature and precipitation information for that day.
    - The function uses the `get_response` function to retrieve data from the weather API.
    - The function uses the `DayDetails`, `Condition`, and `Location` models to validate and parse the received data.
    """

    try:
        log.info(f"User requested weather statistic: {status_user['city']}")
        today_date = date.today()
        for days in range(1, 8):
            statistic_date = today_date - timedelta(days=days)
            url_statistic = f'https://api.weatherapi.com/v1/history.json?key={config.API_KEY}&q={status_user["city"]}&dt={statistic_date}'
            data = await get_response(message, url_statistic, bot)
            day_details = DayDetails.model_validate(data['forecast']['forecastday'][0]['day'])
            day_details_data = data['forecast']['forecastday'][0]['date']
            precipitation = Condition.model_validate(data['forecast']['forecastday'][0]['day']['condition'])
            location = Location.model_validate(data['location'])
            msg_statistic = (
                f"{location.name} ({location.region}): {day_details_data}\n"
                f"Temperature: Max: {day_details.maxtemp_c}°C, Min: {day_details.mintemp_c}°C, {precipitation.text} \n"
            )
            await bot.send_message(message.chat.id, msg_statistic)
        log.info(f"statistic : Success")
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(traceback.format_exc())
        await bot.send_message(message.chat.id, f"Error")
        count_instance_errors.labels(instance=instance_id).inc()
    except ValidationError as e:
        validation_error.labels(instance=instance_id).inc(0)
        await bot.send_message(message.chat.id, f"Error")
        log.error(f"statistic : Validation error {e}")


async def prediction(message: Message, bot: AsyncTeleBot, config: Settings, status_user: dict) -> None:
    """
    A function to make weather predictions based on historical data and forecast for a specific city.
    """
    try:
        today_date = date.today()
        log.info(f"User requested weather prediction: {status_user['city']}")

        # Calculate average temperature for the last 7 days
        avgtemp_c_7days = await calculate_avg_temp_7days(message, today_date, status_user, config, bot)

        # Calculate average temperature for the next 3 days
        avgtemp_c_3days = await calculate_avg_temp_3days(message, status_user, config, bot)

        # Formulate the message to be sent
        if avgtemp_c_7days < avgtemp_c_3days:
            temperature_difference = avgtemp_c_3days - avgtemp_c_7days
            await bot.send_message(message.chat.id,
                                   f"The average temperature in the next 3 days will be {avgtemp_c_3days}°C, "
                                   f"which is {temperature_difference}°C warmer than the last week")
        elif avgtemp_c_7days > avgtemp_c_3days:
            temperature_difference = avgtemp_c_7days - avgtemp_c_3days
            await bot.send_message(message.chat.id,
                                   f"The average temperature in the next 3 days will be {avgtemp_c_3days}°C, "
                                   f"which is {temperature_difference}°C colder than the last week")
        else:
            await bot.send_message(message.chat.id,
                                   f"The average temperature in the next 3 days will be {avgtemp_c_3days}°C,"
                                   f" the temperature remains the same as in the last 7 days")
        log.info(f"Prediction : Success")

    except ZeroDivisionError as e:
        await bot.send_message(message.chat.id, f"Error, please try again")
        log.error(f"statistic : Validation error {e}")
    except Exception as e:
        count_instance_errors.labels(instance=instance_id).inc()
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
        await bot.send_message(message.chat.id, f"Error, please try again later")
