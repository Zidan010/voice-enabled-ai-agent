import os
import json
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import time
from datetime import datetime
from dotenv import load_dotenv

# Import function agents
from function_agents import WeatherAgent, FinanceAgent


class UnifiedAgentSystem:
    """
    Unified 7-Agent RAG System with LangChain + Groq
    
    Agents:
    - 5 Document Agents (FAISS retrieval)
    - 2 Function Agents (API calls)
    """
    
    def __init__(
        self,
        vector_store_dir: str = "vector_store",
        groq_api_key: Optional[str] = None,
        openweather_api_key: Optional[str] = None
    ):
        """
        Initialize the unified agent system
        
        Args:
            vector_store_dir: Path to vector store
            groq_api_key: Groq API key
            openweather_api_key: OpenWeatherMap API key (optional)
        """
        print(f"\n{'='*80}")
        print("INITIALIZING UNIFIED 7-AGENT RAG SYSTEM")
        print(f"{'='*80}")
        load_dotenv()
        # Set API keys
        api_key = os.getenv("GROQ_API_KEY")
        # if not self.groq_api_key:
        #     raise ValueError("GROQ_API_KEY not found. Set it as environment variable or pass it to constructor.")
        
        # Initialize Groq LLM
        print("\n1. Initializing Groq LLM...")
        self.llm = ChatGroq(
            api_key=api_key,
            model_name="llama-3.3-70b-versatile",  # Fast and capable
            temperature=0.1,
            max_tokens=2048
        )
        print("   ✓ Groq LLM initialized (llama-3.3-70b-versatile)")
        
        # Load vector store
        print("\n2. Loading Vector Store...")
        self.vector_store_dir = Path(vector_store_dir)
        
        # Load agent registry
        registry_path = self.vector_store_dir / "agent_registry.json"
        with open(registry_path, 'r', encoding='utf-8') as f:
            self.registry = json.load(f)
        
        # Load embedding model
        embedding_model = self.registry['config']['embedding_model']
        print(f"   Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        print(f"   ✓ Embedding model loaded")
        
        # Document agents
        self.document_agents = [
            "Artificial_Intelligence",
            "Cybersecurity",
            "Digital_Health",
            "Human_Development",
            "Renewable_Energy_Jobs"
        ]
        
        # Initialize function agents
        print("\n3. Initializing Function Agents...")
        self.weather_agent = WeatherAgent(api_key=openweather_api_key)
        self.finance_agent = FinanceAgent()
        print("   ✓ Weather Agent initialized")
        print("   ✓ Finance Agent initialized")
        
        # All agents
        self.all_agents = self.document_agents + ["Weather_Agent", "Finance_Agent"]
        
        # Cache for loaded indices
        self._index_cache = {}
        self._metadata_cache = {}
        
        print(f"\n{'='*80}")
        print(f"✓ System Ready with {len(self.all_agents)} agents")
        print(f"  - Document Agents: {len(self.document_agents)}")
        print(f"  - Function Agents: 2")
        print(f"{'='*80}\n")
    
    def _load_agent_index(self, agent_id: str):
        """Load FAISS index and metadata for an agent"""
        if agent_id in self._index_cache:
            return self._index_cache[agent_id], self._metadata_cache[agent_id]
        
        agent_info = self.registry['agents'][agent_id]
        index_path = self.vector_store_dir / agent_info['index_path']
        metadata_path = self.vector_store_dir / agent_info['metadata_path']
        
        # Load index and metadata
        index = faiss.read_index(str(index_path))
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Cache
        self._index_cache[agent_id] = index
        self._metadata_cache[agent_id] = metadata
        
        return index, metadata
    
    def route_query(self, query: str) -> Dict:
        """
        Use Groq LLM to route query to appropriate agent(s)
        
        Args:
            query: User query
            
        Returns:
            Dictionary with selected agents and reasoning
        """
        # Build agent descriptions
        agent_descriptions = []
        for agent_id in self.all_agents:
            if agent_id in self.document_agents:
                info = self.registry['agents'][agent_id]
                agent_descriptions.append(
                    f"- {agent_id}: {info['description']}"
                )
            elif agent_id == "Weather_Agent":
                agent_descriptions.append(
                    f"- Weather_Agent: {self.weather_agent.description}"
                )
            elif agent_id == "Finance_Agent":
                agent_descriptions.append(
                    f"- Finance_Agent: {self.finance_agent.description}"
                )
        
        # Create routing prompt
        routing_prompt = f"""You are an intelligent query router. Analyze the user's query and determine which specialized agent(s) should handle it.

Available Agents:
{chr(10).join(agent_descriptions)}

Rules:
1. Select 1-3 most relevant agents based on query topic
2. For weather queries → select Weather_Agent
3. For stock/finance queries → select Finance_Agent
4. For AI/ML/technology queries → select Artificial_Intelligence
5. For security/cyber topics → select Cybersecurity
6. For healthcare/medical topics → select Digital_Health
7. For development/poverty/education → select Human_Development
8. For renewable energy/jobs → select Renewable_Energy_Jobs
9. If query spans multiple domains, select multiple agents
10. Return ONLY valid JSON, no other text

User Query: "{query}"

Return your response as JSON:
{{
    "agents": ["agent_id1", "agent_id2"],
    "reasoning": "brief explanation of why these agents were selected"
}}"""
        
        try:
            # Call Groq
            messages = [
                SystemMessage(content="You are a precise query routing system. Return only valid JSON."),
                HumanMessage(content=routing_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            routing_result = json.loads(response_text)
            
            # Validate agents
            selected_agents = routing_result.get("agents", [])
            valid_agents = [a for a in selected_agents if a in self.all_agents]
            
            if not valid_agents:
                # Fallback: select most relevant document agent
                valid_agents = ["Artificial_Intelligence"]
                routing_result["reasoning"] = "Fallback to AI agent due to routing uncertainty"
            
            routing_result["agents"] = valid_agents
            
            return routing_result
            
        except Exception as e:
            print(f"⚠️ Routing error: {e}")
            # Fallback routing
            return {
                "agents": ["Artificial_Intelligence"],
                "reasoning": f"Fallback routing due to error: {str(e)}"
            }
    
    def retrieve_from_document_agent(self, agent_id: str, query: str, k: int = 2) -> List[Dict]:
        """
        Retrieve documents from a document agent's FAISS index
        
        Args:
            agent_id: Agent identifier
            query: Query text
            k: Number of results
            
        Returns:
            List of retrieved chunks
        """
        # Load index and metadata
        index, metadata = self._load_agent_index(agent_id)
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Search
        scores, indices = index.search(query_embedding.astype('float32'), k)
        
        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(metadata['chunks']):
                chunk = metadata['chunks'][idx].copy()
                chunk['score'] = float(score)
                chunk['agent_id'] = agent_id
                chunk['agent_name'] = metadata['agent_name']
                results.append(chunk)
        
        return results
    
    def execute_function_agent(self, agent_id: str, query: str) -> str:
        """
        Execute a function agent
        
        Args:
            agent_id: Agent identifier (Weather_Agent or Finance_Agent)
            query: Query text
            
        Returns:
            Agent response
        """
        if agent_id == "Weather_Agent":
            # Extract location from query (simple approach)
            # You can make this more sophisticated with NER
            location = "Dhaka"  # Default
            
            # Simple location extraction
            query_lower = query.lower()
            if "in " in query_lower:
                parts = query_lower.split("in ")
                if len(parts) > 1:
                    location = parts[1].split()[0].strip("?.,!").title()
            
            return self.weather_agent.execute(location)
        
        elif agent_id == "Finance_Agent":
            # Extract stock symbol or use "market" for summary
            query_upper = query.upper()
            
            # Check for common stock symbols
            import re
            symbols = re.findall(r'\b[A-Z]{1,5}\b', query_upper)
            
            if symbols:
                return self.finance_agent.execute(symbols[0])
            elif any(word in query.lower() for word in ["market", "indices", "summary"]):
                return self.finance_agent.execute("market")
            else:
                # Try to extract from query
                words = query.split()
                for word in words:
                    if word.isupper() and 1 <= len(word) <= 5:
                        return self.finance_agent.execute(word)
                
                # Default to market summary
                return self.finance_agent.execute("market")
        
        return f"Unknown function agent: {agent_id}"
    
    def execute_agents(self, agent_ids: List[str], query: str) -> Dict:
        """
        Execute selected agents
        
        Args:
            agent_ids: List of agent IDs to execute
            query: User query
            
        Returns:
            Dictionary of agent results
        """
        results = {}
        
        for agent_id in agent_ids:
            if agent_id in self.document_agents:
                # Document agent - retrieve from FAISS
                chunks = self.retrieve_from_document_agent(agent_id, query, k=2)
                results[agent_id] = {
                    "type": "document",
                    "chunks": chunks
                }
            elif agent_id in ["Weather_Agent", "Finance_Agent"]:
                # Function agent - execute API call
                response = self.execute_function_agent(agent_id, query)
                results[agent_id] = {
                    "type": "function",
                    "response": response
                }
        
        return results
    
    def format_context(self, agent_results: Dict) -> str:
        """
        Format agent results as context for LLM
        
        Args:
            agent_results: Results from agents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for agent_id, result in agent_results.items():
            if result["type"] == "document":
                # Document agent results
                agent_name = result["chunks"][0]["agent_name"] if result["chunks"] else agent_id
                context_parts.append(f"\n{'='*60}")
                context_parts.append(f"Source: {agent_name}")
                context_parts.append(f"{'='*60}")
                
                for i, chunk in enumerate(result["chunks"], 1):
                    section = " > ".join(chunk['section_path']) if chunk.get('section_path') else "N/A"
                    context_parts.append(f"\n[Chunk {i}]")
                    context_parts.append(f"Section: {section}")
                    context_parts.append(f"Relevance: {chunk['score']:.4f}")
                    context_parts.append(f"\n{chunk['content']}\n")
            
            elif result["type"] == "function":
                # Function agent results
                context_parts.append(f"\n{'='*60}")
                context_parts.append(f"Real-time Data: {agent_id}")
                context_parts.append(f"{'='*60}")
                context_parts.append(f"\n{result['response']}\n")
        
        return "\n".join(context_parts)
    
    def generate_response(self, query: str, context: str) -> str:
        """
        Generate final response using Groq LLM
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Generated response
        """
        generation_prompt = f"""You are a helpful AI assistant. Answer the user's question based on the provided context.

Context:
{context}

User Question: {query}

Instructions:
1. Answer directly and concisely based on the context
2. If the context contains real-time data (weather/finance), include it in your response
3. Cite specific sources when relevant (e.g., "According to the AI report..." or "Based on current weather data...")
4. If the context doesn't fully answer the question, say so honestly
5. Be conversational but informative

Answer:"""
        
        try:
            messages = [
                SystemMessage(content="You are a knowledgeable AI assistant that provides accurate, helpful responses based on given context."),
                HumanMessage(content=generation_prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def query(self, user_query: str, verbose: bool = True) -> Dict:
        """
        Main query processing pipeline
        
        Args:
            user_query: User's question
            verbose: Print detailed progress
            
        Returns:
            Dictionary with results and metadata
        """
        if verbose:
            print(f"\n{'='*80}")
            print(f"Query: {user_query}")
            print(f"{'='*80}")
        
        start_time = time.time()
        
        # Step 1: Route query
        if verbose:
            print("\n1. Routing query to agents...")
        
        route_start = time.time()
        routing = self.route_query(user_query)
        route_time = time.time() - route_start
        
        selected_agents = routing["agents"]
        
        if verbose:
            print(f"   Selected agents: {', '.join(selected_agents)}")
            print(f"   Reasoning: {routing['reasoning']}")
            print(f"   Time: {route_time:.3f}s")
        
        # Step 2: Execute agents
        if verbose:
            print("\n2. Executing agents...")
        
        exec_start = time.time()
        agent_results = self.execute_agents(selected_agents, user_query)
        exec_time = time.time() - exec_start
        
        if verbose:
            for agent_id, result in agent_results.items():
                if result["type"] == "document":
                    print(f"   {agent_id}: Retrieved {len(result['chunks'])} chunks")
                else:
                    print(f"   {agent_id}: Function executed")
            print(f"   Time: {exec_time:.3f}s")
        
        # Step 3: Format context
        context = self.format_context(agent_results)
        
        # Step 4: Generate response
        if verbose:
            print("\n3. Generating response...")
        
        gen_start = time.time()
        response = self.generate_response(user_query, context)
        gen_time = time.time() - gen_start
        
        if verbose:
            print(f"   Time: {gen_time:.3f}s")
        
        total_time = time.time() - start_time
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"Total time: {total_time:.3f}s")
            print(f"{'='*80}")
        
        return {
            "query": user_query,
            "routing": routing,
            "agent_results": agent_results,
            "context": context,
            "response": response,
            "metrics": {
                "route_time": route_time,
                "execution_time": exec_time,
                "generation_time": gen_time,
                "total_time": total_time
            }
        }


def main():
    """Test the system"""
    
    # Initialize system
    system = UnifiedAgentSystem(
        vector_store_dir="vector_store",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        openweather_api_key=os.getenv("OPENWEATHER_API_KEY")  # Optional
    )
    
    # Test queries
    test_queries = [
        "What is artificial intelligence?",
        "What's the weather in Dhaka?",
        "How is AAPL stock doing?",
        "How does AI impact healthcare?",
        "Tell me about renewable energy jobs"
    ]
    
    print("\n" + "="*80)
    print("TESTING QUERIES")
    print("="*80)
    
    for query in test_queries:
        result = system.query(query, verbose=True)
        
        print(f"\nResponse:")
        print("-" * 80)
        print(result["response"])
        print("\n" + "="*80 + "\n")
        
        # Wait a bit between queries
        time.sleep(2)


if __name__ == "__main__":
    main()