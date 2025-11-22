import requests
import json
from typing import Dict, Optional
from datetime import datetime
import yfinance as yf
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENWEATHER_API_KEY")
class WeatherAgent:
    """
    Real-time weather data agent using OpenWeatherMap API
    Free tier: 1000 calls/day
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Weather Agent
        
        Args:
            api_key: OpenWeatherMap API key (get free at https://openweathermap.org/api)
        """
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.agent_id = "Weather_Agent"
        self.agent_name = "Weather Agent"
        self.description = "Provides real-time weather information for any location including temperature, conditions, humidity, and forecast"
    
    def get_current_weather(self, location: str, units: str = "metric") -> Dict:
        """
        Get current weather for a location
        
        Args:
            location: City name (e.g., "Dhaka", "London", "New York")
            units: "metric" (Celsius) or "imperial" (Fahrenheit)
            
        Returns:
            Dictionary with weather data
        """
        if not self.api_key:
            return {
                "error": "OpenWeatherMap API key not configured",
                "message": "Please set OPENWEATHER_API_KEY environment variable",
                "demo_data": self._get_demo_weather(location)
            }
        
        try:
            endpoint = f"{self.base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": units
            }
            
            response = requests.get(endpoint, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            # Format response
            weather_info = {
                "location": data["name"],
                "country": data["sys"]["country"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "wind_speed": data["wind"]["speed"],
                "clouds": data["clouds"]["all"],
                "timestamp": datetime.fromtimestamp(data["dt"]).strftime("%Y-%m-%d %H:%M:%S"),
                "units": "°C" if units == "metric" else "°F"
            }
            
            return {
                "success": True,
                "data": weather_info,
                "formatted": self._format_weather(weather_info)
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "error": f"API request failed: {str(e)}",
                "demo_data": self._get_demo_weather(location)
            }
    
    def _format_weather(self, weather: Dict) -> str:
        """Format weather data as readable text"""
        return (
            f"Weather in {weather['location']}, {weather['country']}:\n"
            f"  Temperature: {weather['temperature']}{weather['units']}\n"
            f"  Feels like: {weather['feels_like']}{weather['units']}\n"
            f"  Condition: {weather['condition']} ({weather['description']})\n"
            f"  Humidity: {weather['humidity']}%\n"
            f"  Wind Speed: {weather['wind_speed']} m/s\n"
            f"  Pressure: {weather['pressure']} hPa\n"
            f"  Cloud Cover: {weather['clouds']}%\n"
            f"  Last Updated: {weather['timestamp']}"
        )
    
    def _get_demo_weather(self, location: str) -> Dict:
        """Return demo weather data when API key not available"""
        return {
            "location": location,
            "country": "XX",
            "temperature": 28.5,
            "feels_like": 31.2,
            "condition": "Cloudy",
            "description": "scattered clouds",
            "humidity": 75,
            "pressure": 1010,
            "wind_speed": 3.5,
            "clouds": 40,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "units": "°C",
            "note": "This is demo data. Configure API key for real-time data."
        }
    
    def execute(self, location: str = "Dhaka") -> str:
        """
        Main execution method for agent
        
        Args:
            location: Location to get weather for
            
        Returns:
            Formatted weather information
        """
        result = self.get_current_weather(location)
        
        if result.get("success"):
            return result["formatted"]
        elif result.get("demo_data"):
            demo = result["demo_data"]
            return (
                f"⚠️ Using demo data (API key not configured)\n\n"
                f"{self._format_weather(demo)}"
            )
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"


class FinanceAgent:
    """
    Real-time finance data agent using Yahoo Finance (via yfinance)
    No API key needed - Free unlimited access
    """
    
    def __init__(self):
        """Initialize Finance Agent"""
        self.agent_id = "Finance_Agent"
        self.agent_name = "Finance Agent"
        self.description = "Provides real-time stock prices, market data, financial metrics, and company information for any publicly traded company"
    
    def get_stock_data(self, symbol: str) -> Dict:
        """
        Get stock data for a symbol
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL", "TSLA")
            
        Returns:
            Dictionary with stock data
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            history = stock.history(period="1d")
            
            if history.empty:
                return {
                    "error": f"No data found for symbol: {symbol}",
                    "suggestion": "Please check the ticker symbol and try again"
                }
            
            # Get current price
            current_price = history['Close'].iloc[-1]
            open_price = history['Open'].iloc[-1]
            high_price = history['High'].iloc[-1]
            low_price = history['Low'].iloc[-1]
            volume = history['Volume'].iloc[-1]
            
            # Calculate change
            prev_close = info.get('previousClose', open_price)
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
            
            stock_data = {
                "symbol": symbol.upper(),
                "name": info.get('longName', symbol.upper()),
                "current_price": round(current_price, 2),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "previous_close": round(prev_close, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": int(volume),
                "market_cap": info.get('marketCap', 'N/A'),
                "currency": info.get('currency', 'USD'),
                "exchange": info.get('exchange', 'N/A'),
                "sector": info.get('sector', 'N/A'),
                "industry": info.get('industry', 'N/A'),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return {
                "success": True,
                "data": stock_data,
                "formatted": self._format_stock_data(stock_data)
            }
            
        except Exception as e:
            return {
                "error": f"Failed to fetch stock data: {str(e)}",
                "suggestion": "Please verify the ticker symbol is correct"
            }
    
    def get_market_summary(self) -> Dict:
        """Get major market indices summary"""
        indices = {
            "S&P 500": "^GSPC",
            "Dow Jones": "^DJI",
            "NASDAQ": "^IXIC"
        }
        
        summary = {}
        
        for name, symbol in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d")
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    open_price = hist['Open'].iloc[-1]
                    change = current - open_price
                    change_percent = (change / open_price) * 100
                    
                    summary[name] = {
                        "value": round(current, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2)
                    }
            except:
                summary[name] = {"error": "Data unavailable"}
        
        return {
            "success": True,
            "data": summary,
            "formatted": self._format_market_summary(summary)
        }
    
    def _format_stock_data(self, data: Dict) -> str:
        """Format stock data as readable text"""
        change_symbol = "📈" if data['change'] >= 0 else "📉"
        
        market_cap = data['market_cap']
        if isinstance(market_cap, (int, float)):
            if market_cap >= 1e12:
                market_cap = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                market_cap = f"${market_cap/1e9:.2f}B"
            elif market_cap >= 1e6:
                market_cap = f"${market_cap/1e6:.2f}M"
        
        return (
            f"{data['name']} ({data['symbol']})\n"
            f"  Current Price: {data['currency']} {data['current_price']}\n"
            f"  {change_symbol} Change: {data['change']:+.2f} ({data['change_percent']:+.2f}%)\n"
            f"  Day Range: {data['low']} - {data['high']}\n"
            f"  Previous Close: {data['previous_close']}\n"
            f"  Volume: {data['volume']:,}\n"
            f"  Market Cap: {market_cap}\n"
            f"  Exchange: {data['exchange']}\n"
            f"  Sector: {data['sector']}\n"
            f"  Industry: {data['industry']}\n"
            f"  Last Updated: {data['timestamp']}"
        )
    
    def _format_market_summary(self, summary: Dict) -> str:
        """Format market summary as readable text"""
        lines = ["Market Summary:"]
        
        for name, data in summary.items():
            if "error" not in data:
                symbol = "📈" if data['change'] >= 0 else "📉"
                lines.append(
                    f"  {name}: {data['value']:,.2f} "
                    f"{symbol} {data['change']:+.2f} ({data['change_percent']:+.2f}%)"
                )
            else:
                lines.append(f"  {name}: Data unavailable")
        
        return "\n".join(lines)
    
    def execute(self, query: str = "") -> str:
        """
        Main execution method for agent
        
        Args:
            query: Stock symbol or "market" for market summary
            
        Returns:
            Formatted financial information
        """
        # If query is "market" or empty, show market summary
        if not query or query.lower() in ["market", "summary", "indices"]:
            result = self.get_market_summary()
            return result.get("formatted", "Unable to fetch market data")
        
        # Otherwise, treat as stock symbol
        result = self.get_stock_data(query)
        
        if result.get("success"):
            return result["formatted"]
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"


def test_agents():
    """Test function agents"""
    print("="*80)
    print("TESTING FUNCTION AGENTS")
    print("="*80)
    
    # Test Weather Agent
    print("\n1. Testing Weather Agent")
    print("-" * 80)
    weather_agent = WeatherAgent()
    print(weather_agent.execute("Dhaka"))
    print("\n" + weather_agent.execute("London"))
    
    # Test Finance Agent
    print("\n" + "="*80)
    print("2. Testing Finance Agent")
    print("-" * 80)
    finance_agent = FinanceAgent()
    print(finance_agent.execute("AAPL"))
    print("\n" + finance_agent.execute("GOOGL"))
    print("\n" + finance_agent.execute("market"))
    
    print("\n" + "="*80)
    print("✓ Function Agents Test Complete")
    print("="*80)


if __name__ == "__main__":
    test_agents()