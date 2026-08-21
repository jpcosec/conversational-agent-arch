from google.adk import Agent


def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city: The name of the city for which to retrieve the weather report.

    Returns:
        dict with status and report or error_message.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }


root_agent = Agent(
    name="weather_time_agent",
    instruction="I can answer your questions about the time and weather in a city.",
    tools=[get_weather],
)