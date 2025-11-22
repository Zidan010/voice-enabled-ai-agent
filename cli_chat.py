#!/usr/bin/env python3
"""
CLI Interactive Chat Interface for 7-Agent RAG System
"""

import os
import sys
from pathlib import Path
from langchain_groq_rag import UnifiedAgentSystem
from datetime import datetime
import json

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class CLIChatInterface:
    """Interactive CLI chat interface"""
    
    def __init__(self):
        """Initialize chat interface"""
        self.system = None
        self.chat_history = []
        self.session_start = datetime.now()
    
    def print_banner(self):
        """Print welcome banner"""
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                   🤖 7-AGENT RAG CHAT SYSTEM 🤖                           ║
║                                                                           ║
║                    Powered by LangChain + Groq                            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
{Colors.END}

{Colors.YELLOW}Available Agents:{Colors.END}
  📚 Document Agents:
     • Artificial_Intelligence - AI, ML, Deep Learning, Applications
     • Cybersecurity - Security frameworks, NIST, Risk management
     • Digital_Health - Healthcare tech, Telemedicine, Health data
     • Human_Development - Poverty, Education, Social welfare
     • Renewable_Energy_Jobs - Green jobs, Solar, Wind, Sustainability
  
  🌐 Function Agents:
     • Weather_Agent - Real-time weather data for any location
     • Finance_Agent - Real-time stock prices and market data

{Colors.GREEN}Commands:{Colors.END}
  • Type your question and press Enter
  • '/help' - Show this help message
  • '/agents' - List all agents
  • '/history' - Show chat history
  • '/clear' - Clear screen
  • '/stats' - Show session statistics
  • '/exit' or '/quit' - Exit the chat

{Colors.CYAN}{'='*79}{Colors.END}
"""
        print(banner)
    
    def initialize_system(self):
        """Initialize the agent system"""
        print(f"\n{Colors.YELLOW}Initializing system...{Colors.END}")
        
        # Check for API keys
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            print(f"{Colors.RED}❌ Error: GROQ_API_KEY not found!{Colors.END}")
            print(f"{Colors.YELLOW}Please set it in your environment:{Colors.END}")
            print(f"  export GROQ_API_KEY='your-api-key-here'")
            sys.exit(1)
        
        weather_key = os.getenv("OPENWEATHER_API_KEY")
        if not weather_key:
            print(f"{Colors.YELLOW}⚠️  OpenWeatherMap API key not found (weather will use demo data){Colors.END}")
        
        # Initialize system
        try:
            self.system = UnifiedAgentSystem(
                vector_store_dir="vector_store",
                groq_api_key=groq_key,
                openweather_api_key=weather_key
            )
            print(f"{Colors.GREEN}✓ System initialized successfully!{Colors.END}\n")
        except Exception as e:
            print(f"{Colors.RED}❌ Error initializing system: {e}{Colors.END}")
            sys.exit(1)
    
    def print_help(self):
        """Print help message"""
        help_text = f"""
{Colors.CYAN}{'='*79}
HELP - Available Commands
{'='*79}{Colors.END}

{Colors.GREEN}Query Commands:{Colors.END}
  • Just type your question naturally and press Enter
  • Examples:
    - "What is artificial intelligence?"
    - "What's the weather in Dhaka?"
    - "How is Apple stock doing?"
    - "Tell me about renewable energy jobs"
    - "How does AI impact healthcare?"

{Colors.GREEN}System Commands:{Colors.END}
  • /help      - Show this help message
  • /agents    - List all available agents
  • /history   - Show conversation history
  • /clear     - Clear the screen
  • /stats     - Show session statistics
  • /exit      - Exit the chat
  • /quit      - Exit the chat

{Colors.CYAN}{'='*79}{Colors.END}
"""
        print(help_text)
    
    def list_agents(self):
        """List all available agents"""
        print(f"\n{Colors.CYAN}{'='*79}")
        print("AVAILABLE AGENTS")
        print(f"{'='*79}{Colors.END}\n")
        
        print(f"{Colors.GREEN}📚 Document Agents (5):{Colors.END}")
        for agent_id in self.system.document_agents:
            info = self.system.registry['agents'][agent_id]
            print(f"  • {Colors.BOLD}{agent_id}{Colors.END}")
            print(f"    {info['description'][:100]}...")
            print()
        
        print(f"{Colors.GREEN}🌐 Function Agents (2):{Colors.END}")
        print(f"  • {Colors.BOLD}Weather_Agent{Colors.END}")
        print(f"    {self.system.weather_agent.description}")
        print()
        print(f"  • {Colors.BOLD}Finance_Agent{Colors.END}")
        print(f"    {self.system.finance_agent.description}")
        print()
        
        print(f"{Colors.CYAN}{'='*79}{Colors.END}\n")
    
    def show_history(self):
        """Show chat history"""
        if not self.chat_history:
            print(f"\n{Colors.YELLOW}No chat history yet.{Colors.END}\n")
            return
        
        print(f"\n{Colors.CYAN}{'='*79}")
        print("CHAT HISTORY")
        print(f"{'='*79}{Colors.END}\n")
        
        for i, entry in enumerate(self.chat_history, 1):
            print(f"{Colors.BOLD}[{i}] {entry['timestamp']}{Colors.END}")
            print(f"{Colors.YELLOW}Q:{Colors.END} {entry['query']}")
            print(f"{Colors.GREEN}Agents:{Colors.END} {', '.join(entry['agents'])}")
            print(f"{Colors.BLUE}Time:{Colors.END} {entry['time']:.2f}s")
            print(f"{Colors.GREEN}A:{Colors.END} {entry['response'][:150]}...")
            print()
        
        print(f"{Colors.CYAN}{'='*79}{Colors.END}\n")
    
    def show_stats(self):
        """Show session statistics"""
        if not self.chat_history:
            print(f"\n{Colors.YELLOW}No statistics yet. Start chatting!{Colors.END}\n")
            return
        
        total_queries = len(self.chat_history)
        total_time = sum(e['time'] for e in self.chat_history)
        avg_time = total_time / total_queries
        
        # Count agent usage
        agent_usage = {}
        for entry in self.chat_history:
            for agent in entry['agents']:
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
        
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        print(f"\n{Colors.CYAN}{'='*79}")
        print("SESSION STATISTICS")
        print(f"{'='*79}{Colors.END}\n")
        
        print(f"{Colors.GREEN}Session Info:{Colors.END}")
        print(f"  • Started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  • Duration: {session_duration:.0f}s ({session_duration/60:.1f} minutes)")
        print(f"  • Total Queries: {total_queries}")
        print()
        
        print(f"{Colors.GREEN}Performance:{Colors.END}")
        print(f"  • Total Processing Time: {total_time:.2f}s")
        print(f"  • Average Query Time: {avg_time:.2f}s")
        print()
        
        print(f"{Colors.GREEN}Agent Usage:{Colors.END}")
        for agent, count in sorted(agent_usage.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {agent}: {count} times")
        print()
        
        print(f"{Colors.CYAN}{'='*79}{Colors.END}\n")
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        self.print_banner()
    
    def process_command(self, command: str) -> bool:
        """
        Process special commands
        
        Returns:
            True if should continue, False if should exit
        """
        command = command.lower().strip()
        
        if command in ['/exit', '/quit']:
            return False
        elif command == '/help':
            self.print_help()
        elif command == '/agents':
            self.list_agents()
        elif command == '/history':
            self.show_history()
        elif command == '/stats':
            self.show_stats()
        elif command == '/clear':
            self.clear_screen()
        else:
            print(f"{Colors.RED}Unknown command: {command}{Colors.END}")
            print(f"Type '/help' for available commands\n")
        
        return True
    
    def process_query(self, query: str):
        """Process user query"""
        try:
            # Show processing indicator
            print(f"\n{Colors.YELLOW}🤔 Processing your query...{Colors.END}\n")
            
            # Query the system
            result = self.system.query(query, verbose=False)
            
            # Display routing info
            print(f"{Colors.CYAN}╔{'═'*77}╗")
            print(f"║ {Colors.BOLD}Routing Information{' '*57}{Colors.END}{Colors.CYAN}║")
            print(f"╠{'═'*77}╣{Colors.END}")
            print(f"{Colors.CYAN}║{Colors.END} {Colors.GREEN}Selected Agents:{Colors.END} {', '.join(result['routing']['agents']):<52} {Colors.CYAN}║{Colors.END}")
            print(f"{Colors.CYAN}║{Colors.END} {Colors.GREEN}Reasoning:{Colors.END} {result['routing']['reasoning'][:60]:<60} {Colors.CYAN}║{Colors.END}")
            print(f"{Colors.CYAN}╚{'═'*77}╝{Colors.END}\n")
            
            # Display response
            print(f"{Colors.GREEN}{Colors.BOLD}Response:{Colors.END}")
            print(f"{Colors.CYAN}{'─'*79}{Colors.END}")
            print(result['response'])
            print(f"{Colors.CYAN}{'─'*79}{Colors.END}\n")
            
            # Display metrics
            metrics = result['metrics']
            print(f"{Colors.BLUE}⏱️  Performance:{Colors.END} " +
                  f"Route: {metrics['route_time']:.2f}s | " +
                  f"Execute: {metrics['execution_time']:.2f}s | " +
                  f"Generate: {metrics['generation_time']:.2f}s | " +
                  f"Total: {metrics['total_time']:.2f}s\n")
            
            # Save to history
            self.chat_history.append({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'query': query,
                'agents': result['routing']['agents'],
                'response': result['response'],
                'time': metrics['total_time']
            })
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error processing query: {e}{Colors.END}\n")
    
    def run(self):
        """Main chat loop"""
        self.clear_screen()
        self.initialize_system()
        
        print(f"{Colors.GREEN}Ready! Type your question or '/help' for commands.{Colors.END}\n")
        
        while True:
            try:
                # Get user input
                user_input = input(f"{Colors.BOLD}{Colors.CYAN}You: {Colors.END}").strip()
                
                # Skip empty input
                if not user_input:
                    continue
                
                # Check for commands
                if user_input.startswith('/'):
                    if not self.process_command(user_input):
                        # Exit command
                        print(f"\n{Colors.GREEN}Thank you for using the 7-Agent RAG System!{Colors.END}")
                        print(f"{Colors.YELLOW}Goodbye! 👋{Colors.END}\n")
                        break
                    continue
                
                # Process as query
                self.process_query(user_input)
                
            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}Interrupted by user.{Colors.END}")
                print(f"{Colors.GREEN}Goodbye! 👋{Colors.END}\n")
                break
            except EOFError:
                print(f"\n{Colors.GREEN}Goodbye! 👋{Colors.END}\n")
                break
            except Exception as e:
                print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}\n")


def main():
    """Entry point"""
    chat = CLIChatInterface()
    chat.run()


if __name__ == "__main__":
    main()