# WeatherForecastBot

WeatherForecastBot is your personal assistant for getting accurate weather forecasts. It provides weather information for any city. Just enter the city name, and the bot will inform you about the weather!

## Featuresa

- Get the current weather information for any city
- Accurate and timely weather data

## 🛠 Technologies

- **Python**: The primary programming language.
- **FastAPI**: For building the web application.
- **asyncpg**: For interacting with the PostgreSQL database.
- **Pydantic**: For data validation and managing settings.
- **Telegram Bot API**: For interacting with Telegram users.
- **Prometheus**: For monitoring and collecting metrics.
- **Grafana**: For visualizing metrics and monitoring data.
- **Loki**: For logging and collecting logs in real-time.
- **Promtail**: For collecting logs and sending them to Loki.

## Installation

Follow these steps to set up and run the project:

### Cloning the Repository

```bash
git clone https://github.com/yourusername/WeatherForecastBot.git
cd WeatherForecastBot
```

## Using Docker

Follow these steps to build and run the Docker container:

### Building Docker Image

Use the following command to build the Docker image:

```bash
docker build -t weather-forecast-bot .
```

### Running Docker Container

Run the Docker container using the following command:

```bash
docker run -d --name weather-forecast-bot -p 8000:8000 weather-forecast-bot
```

This will start the container and map host port 8000 to container port 8000.

## Using Docker Compose

Follow these steps to use Docker Compose to run the project:

### Environment Configuration

Create a `.env` file in the project's root directory and add the necessary environment variables:

```env
TOKEN=your_telegram_bot_token
API_KEY=your_api_key
TG_BOT_API_URL=your_telegram_bot_api_url
APP_DOMAIN=your_app_domain
SECRET_TOKEN_TG_WEBHOOK=your_secret_token
NGROK_AUTHTOKEN=your_ngrok_authtoken
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=your_postgres_db
```

### Obtaining API Keys

1. **Telegram Bot Token**: Get your bot token from [@BotFather](https://core.telegram.org/bots#botfather).
2. **Weather API Key**: Register at [WeatherAPI](https://www.weatherapi.com/) to create a new API key.

### Running Docker Compose

Use the following command to start all services defined in `docker-compose.yml`:

```bash
cd deploy
docker-compose up --build -d
```

This will create and run containers for your application and database, as well as set up a tunnel using Ngrok.

## Entry Point

The main script to start your bot:

```python
import traceback
import uvicorn
import logging
import asyncio
import sys
from src.startup import startup
from postgres.pool import DbPool
from handlers.db_handlers import bd_router
from handlers.tg_handler import webhook_router
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI
from contextlib import asynccontextmanager

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        settings = get_settings()
        logging_config(settings.LOG_LEVEL)
        await DbPool.create_pool()
        pool = await DbPool.get_pool()
        check_bot_token(settings.TOKEN)
        check_api_key(settings.API_KEY)
        set_webhook(settings.TOKEN, settings.APP_DOMAIN, settings.SECRET_TOKEN_TG_WEBHOOK)
        await create_table(pool)
        await inc_counters()
        log.info("Startup completed successfully")

        if not pool:
            log.error("Failed to create database connection pool")
            sys.exit(1)
        yield
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        try:
            await DbPool.close_pool()
        except Exception as e:
            log.error(f"An error occurred while closing the database connection pool: {e}")


app = FastAPI(lifespan=lifespan)
app.include_router(bd_router)
app.include_router(webhook_router)

instrumental = Instrumentator().instrument(app).expose(app, include_in_schema=False, should_gzip=True)

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=get_settings().LISTEN_PORT, log_level=get_settings().LOG_LEVEL_UVICORN)
    except Exception as e:
        log.error(f"error during start: {e}")
        log.debug(traceback.format_exc())
        sys.exit(1)

### Main script tasks:

1. Load settings using `get_settings()`.
2. Configure logging with `logging_config`.
3. Create a database connection pool using `create_pool`.
4. Validate the bot token using `check_bot_token`.
5. Validate the API key using `check_api_key`.
6. Set up the webhook for the Telegram bot using `set_webhook`.
7. Create necessary database tables using `asyncio.run(create_table())`.
8. Start the server using `uvicorn.run`.

## Endpoint to tg_webhook

**Description:**
- The `/tg_webhooks` endpoint is responsible for receiving and processing messages sent to the Telegram bot. It validates incoming requests to ensure they are authorized and correctly formatted. 

**How It Works:**
1. **Authorization**: The endpoint checks the `X-Telegram-Bot-Api-Secret-Token` header against a configured secret token to verify that the request is legitimate.
2. **Request Method**: It only accepts `POST` requests. If a different method is used, it responds with a `405 Method Not Allowed` error.
3. **JSON Parsing**: The request body is expected to be in JSON format. If the JSON parsing fails, it returns a `400 Bad Request` error.
4. **Message Handling**: 
   - The JSON data is transformed into a `Message` object.
   - If the message does not pass validation, a `400 Bad Request` error is returned.
   - The endpoint checks the user's chat ID and determines if the user is waiting for a specific input.
   - Depending on the user's status, it either processes the message or prompts the user for the required input.
5. **Error Handling**: If any errors occur during processing (e.g., validation errors, database errors), they are logged, and a user-friendly message

## Command Handling and Database Interaction

The project includes several functions for handling commands from users and interacting with the PostgreSQL database.

### Module Functions

#### `check_chat_id`

Проверяет наличие `chat_id` в таблице `user_state` и вставляет запись при отсутствии, затем возвращает данные пользователя.

```python
async def check_chat_id(pool: Pool, message):
    """
     Checks the chat_id in the user_state table, inserts if not present, and retrieves the data.
     Args:
         pool (Pool): The asyncpg Pool.
         message: The message object containing chat information.
     Returns:
         dict: The user_state data for the given chat_id.
     """
    try:
        fields = {
            "chat_id": message.chat.id,
            "city": "Moskva",
            "date_difference": "None",
            "qty_days": "None",
        }

        on_conflict = "chat_id"
        builder = SQLQueryBuilder("user_state")
        builder.insert(fields, on_conflict=on_conflict)
        await execute_query(pool, builder.sql, *builder.args, fetch=True)

        builder1 = SQLQueryBuilder("user_state")
        builder1.select(["city", "date_difference", "qty_days"]).where({"chat_id": ("=", message.chat.id)})
        res = await execute_query(pool, builder1.sql1, *builder1.args1, fetch=True)
        decoded_result = [dict(r) for r in res][0]
        log.debug("user_state table updated successfully")
        return decoded_result
    except Exception as e:
        count_instance_errors.labels(instance=instance_id).inc()
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback: \n {traceback.format_exc()}")
```

#### `check_waiting`

Checks user status and performs actions based on the status.

```python
async def check_waiting(status_user: dict, pool, message, bot: AsyncTeleBot, config: Settings):
    try:
        if status_user["city"] == "waiting_value":
            await add_city(pool, message, bot, config)
        if status_user["date_difference"] == "waiting_value":
            await add_day(pool, message, bot, config)
            query = await sql_update_user_state_bd(bot, pool, message, "date_difference", "None")
        if status_user["qty_days"] == "waiting_value":
            await get_forecast_several(pool, message, bot, config)
            query = await sql_update_user_state_bd(bot, pool, message, "qty_days", "None")
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.error("Exception traceback: ", traceback.format_exc())
```

#### `handlers`

Handles different message commands and calls corresponding functions.

```python
async def handlers(pool: Pool, message: Message, bot: AsyncTeleBot, config: Settings, status_user: dict):
    try:
        if message.text == '/start':
            await start_message(pool, message, bot)
            await add_statistic_bd(pool, message)
        elif message.text == '/help':
            await help_message(message, bot)
            await add_statistic_bd(pool, message)
        elif message.text == '/change_city':
            await change_city(pool, message, bot)
            await add_statistic_bd(pool, message)
        elif message.text == '/current_weather':
            await weather(message, bot, config, status_user)
            await add_statistic_bd(pool, message)
        elif message.text == '/weather_forecast':
            await weather_forecast(pool, message, bot)
            await add_statistic_bd(pool, message)
        elif message.text == '/forecast_for_several_days':
            await forecast_for_several_days(pool, message, bot)
            await add_statistic_bd(pool, message)
        elif message.text == '/weather_statistic':
            await statistic(message, bot, config, status_user)
            await add_statistic_bd(pool, message)
        elif message.text == '/prediction':
            await prediction(message, bot, config, status_user)
            await add_statistic_bd(pool, message)
        else:
            unknown_command_counter.labels(instance=instance_id).inc()  # Count the number of unknown commands
            await bot.send_message(message.chat.id, 'Unknown command. Please try again\n/help')
    except Exception as e:
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id,
                               'An error occurred. Please send administrators a message or contact support.')
        log.error("An error occurred: %s", str(e))
        log.debug("Exception traceback", traceback.format_exc())
```

### Main Commands

- **`/start`**: Sends a welcome message to the user and initializes their state in the database.
- **`/help`**: Displays a list of available commands and their descriptions.
- **`/change_city`**: Changes the user's current city.
- **`/current_weather`**: Gets the current weather information for the selected city.
- **`/weather_forecast`**: Gets the weather forecast for a specific date.
- **`/forecast_for_several_days`**: Provides a weather forecast for several days (from 2 to 10).
- **`/weather_statistic`**: Gets weather statistics for the last 7 days.
- **`/prediction`**: Predicts the average temperature for 3 days.

## Endpoint to Get User Actions

The new endpoint `/users_actions` allows you to retrieve user action data from the database based on various criteria.

### Input Parameters

- `chat_id` (int, optional): Chat/User ID.
- `from_ts` (int, optional): Start timestamp.
- `until_ts` (int, optional): End timestamp.
- `limits` (int, optional): Maximum number of results. Default is 1000.
- `credentials` (HTTPBasicCredentials, optional): Security credentials. Default is `Security(verify_credentials)`.
- `pool` (Pool, optional): Global database connection pool. Default is `Depends(create_pool)`.

### Return Value

- `list`: List of user actions retrieved based on the specified criteria.

### Exceptions

- `HTTPException`: Raised if an error occurs during the query execution or unauthorized access.

### Request Example

```bash
# Authorization with credentials in the header
curl -u your_username:your_ password -X 'GET' \
'http://localhost:8000/users_actions?chat_id=12345&from_ts=1609459200&until_ts=1612137600&limits=10' \
-H 'accept: application/json'
```

This request will return user actions with `chat_id` 12345 that occurred between the timestamps `1609459200` and `1612137600`, with a maximum of 10 records.

## Endpoint to Get User Actions Count

The new endpoint `/actions_count` allows you to retrieve the count of user actions from the database based on various criteria.

### Input Parameters

- `chat_id` (int): Chat/User ID.
- `credentials` (HTTPBasicCredentials, optional): Security credentials. Default is `Security(verify_credentials)`.
- `pool` (Pool, optional): Global database connection pool. Default is `Depends(create_pool)`.

### Return Value

- `dict`: Dictionary containing the count of user actions based on the specified criteria.

### Exceptions

- `HTTPException`: Raised if an error occurs during the query execution or unauthorized access.

### Request Example

```bash
# Authorization with credentials in the header
curl -u your_username:your_password -X 'GET' \
'http://localhost:8000/actions_count?chat_id=12345' \
-H 'accept: application/json'
```

This request will return the count of user actions with `chat_id` 12345.

#### Example Output

```json
[
    {
        "chat_id": 859805066,
        "month": "2024-06-01T00:00:00+00:00",
        "actions_count": 26
    },
    {
        "chat_id": 859805066,
        "month": "2024-10-01T00:00:00+00:00",
        "actions_count": 98
    },
    {
        "chat_id": 859805066,
        "month": "2024-09-01T00:00:00+00:00",
        "actions_count": 7
    },
    {
        "chat_id": 859805066,
        "month": "2024-05-01T00:00:00+00:00",
        "actions_count": 5
    }

```

# Monitoring and Logging

This project utilizes the PLG stack for effective monitoring and logging:

- **Promtail**: Used for collecting logs from the application and forwarding them to Loki. Promtail can scrape logs from various sources, making it easy to integrate with your existing logging setup.
- **Loki**: Employed for aggregating logs from the application, providing a centralized logging solution that integrates seamlessly with Grafana.
- **Grafana**: Used for visualizing both metrics and logs, enabling easy creation of dashboards to monitor application performance and troubleshoot issues.

## Promtail and Loki Configuration

Promtail is used to send logs from files, where the Docker logging driver stores logs from all containers in JSON files. Here are the key points of the configuration:

### 1. Log Storage

- **Log Files**: Promtail reads logs from the JSON files generated by the Docker logging driver. This allows for centralized log management and analysis.

### 2. Data Persistence

- **Loki Data Storage**: The directory used by Loki for storing log data is mounted to the host. This ensures data persistence, meaning that logs are retained even after container restarts or removals.

### 3. Configuration Management

- **Configuration Files**: Both Promtail and Loki are configured by mounting `config.yml` files into the containers. This allows for easy updates and management of configuration settings without needing to rebuild the images.



# Provisioning in Grafana

Grafana is configured to use PostgreSQL as its database through environment variables. This allows for flexible and secure database connection management.

In addition to manual setup, data sources in Grafana are provisioned automatically. This ensures that:

- **Data Sources**: Loki and Prometheus are configured as data sources automatically upon startup, reducing the need for manual configuration.
- **Dashboards**: Predefined dashboards are set up to visualize key metrics and logs, providing immediate insights into application performance.

By leveraging this stack and automated provisioning, we ensure that our application is not only monitored for performance but also provides detailed logging for better observability and debugging.

# Prometheus Configuration

Prometheus is used for monitoring and collecting metrics from the application. Here are the main points of the configuration:

### 1. Scrape Configuration

- **Configuration Propagation**: The `scrape config` is passed into the Docker container from the host via a volume. This allows for easy modifications of settings without the need to rebuild the image.
  
- **Metrics Collection**: Docker DNS Service Discovery (SD) is used to collect metrics from all replicas of the main application. This enables Prometheus to automatically discover and collect metrics from dynamically changing instances of the application.

### 2. Data Persistence

- **Data Storage**: The directory used by Prometheus for its internal database (TSDB - Time Series Database) is mounted to the host. This ensures data persistence, meaning that restarting or removing the container does not lead to the loss of collected metrics. Data is retained even after the container is restarted, allowing for historical metric analysis in the future.

### Example Configuration

Here’s an example of a `prometheus.yml` configuration that can be used in your project:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'docker'
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        regex: prometheus
        action: drop
```

