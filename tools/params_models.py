from pydantic import BaseModel, Field

class CalculatorParams(BaseModel):
    expression: str = Field(
        description="Mathematical expression to evaluate (e.g., '2 + 3 * 4')",
        min_length=1
    )

class CurrentDateTimeParams(BaseModel):
    """No parameters needed for this tool."""
    pass

class LocationCoordinatesParams(BaseModel):
    location_name: str = Field(
        description="Name of the location for which coordinates are requested",
        min_length=1
    )

class WeatherParams(BaseModel):
    latitude: str = Field(
        description="Latitude of the location for which current weather is requested",
        min_length=1
    )
    longitude: str = Field(
        description="Longitude of the location for which current weather is requested",
        min_length=1
    )
    metrics: str = Field(
        default="metric",
        description="Unit system for temperature. Options: 'metric' for Celsius, 'imperial' for Fahrenheit, 'standard' for Kelvin.",
        pattern="^(metric|imperial|standard)$"
    )
