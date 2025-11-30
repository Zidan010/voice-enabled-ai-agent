# function_agents.py
import json
import requests
from typing import Dict, Optional, List

class TavilyClient:
    """Simple lightweight Tavily search wrapper."""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Tavily API key missing.")
        self.api_key = api_key
        self.url = "https://api.tavily.com/search"
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic"
        }
        try:
            res = requests.post(self.url, json=payload, timeout=10)
            res.raise_for_status()
            data = res.json()
            return data.get("results", [])
        except Exception as e:
            return [{"title": "Error", "content": f"Tavily request failed: {str(e)}"}]


class WeatherAgent:
    """
    Weather agent powered by Tavily search.
    """

    def __init__(self, tavily_api_key: str):
        self.agent_id = "Weather_Agent"
        self.agent_name = "Weather Agent"
        self.description = "Fetches real-time weather via Tavily search engine."

        self.client = TavilyClient(tavily_api_key)

    def execute(self, location: str) -> str:
        q = f"current weather in {location} today temperature humidity wind speed"
        results = self.client.search(q, max_results=3)

        text = f"Weather results for {location}:\n"
        for r in results:
            text += f"- {r.get('title')}\n  {r.get('content')}\n\n"
        return text.strip()


class FinanceAgent:
    """
    Finance agent powered by Tavily search.
    """

    def __init__(self, tavily_api_key: str):
        self.agent_id = "Finance_Agent"
        self.agent_name = "Finance Agent"
        self.description = "Fetches live stock data / market summaries via Tavily search."

        self.client = TavilyClient(tavily_api_key)

    def execute(self, symbol_or_query: str) -> str:
        q = f"current stock price market summary data for {symbol_or_query}"
        results = self.client.search(q, max_results=3)

        text = f"Financial information for {symbol_or_query}:\n"
        for r in results:
            text += f"- {r.get('title')}\n  {r.get('content')}\n\n"
        return text.strip()
