# cli_chat.py
import os
import sys
from datetime import datetime
from langchain_groq_rag import UnifiedAgentSystem

class CLIChatInterface:

    def __init__(self):
        self.system = None
        self.chat_history = []
        self.start = datetime.now()

    def print_banner(self):
        print("\n==============================================")
        print("        7-Agent RAG Chat System (CLI)")
        print("==============================================")
        print("Agents:")
        print(" • 5 Document Agents")
        print(" • Weather_Agent (Tavily-powered)")
        print(" • Finance_Agent (Tavily-powered)")
        print("----------------------------------------------")
        print("Commands: /help /agents /history /stats /exit")
        print("==============================================\n")

    def initialize(self):
        print("Initializing system...")
        try:
            self.system = UnifiedAgentSystem()
            print("System ready.\n")
        except Exception as e:
            print("Error initializing:", e)
            sys.exit(1)

    def process_query(self, query: str):
        print("\nProcessing...\n")
        result = self.system.query(query, verbose=False)

        print("Routing:")
        print(result["routing"])
        print("\nResponse:\n", result["response"])
        print("\n----------------------------------------------\n")

        self.chat_history.append({
            "query": query,
            "response": result["response"],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

    def run(self):
        self.print_banner()
        self.initialize()

        while True:
            try:
                q = input("You: ").strip()
                if not q:
                    continue

                if q in ["/exit", "/quit"]:
                    print("Goodbye.")
                    break

                if q == "/help":
                    print("Commands: /help /history /agents /stats /exit")
                    continue

                if q == "/agents":
                    print("Agents:")
                    print(self.system.agent_descriptions.keys())
                    continue

                if q == "/history":
                    for h in self.chat_history:
                        print(f"[{h['timestamp']}] {h['query']} → {h['response'][:80]}...")
                    continue

                if q == "/stats":
                    print(f"Total queries: {len(self.chat_history)}")
                    continue

                # normal query
                self.process_query(q)

            except KeyboardInterrupt:
                print("\nGoodbye.")
                break


if __name__ == "__main__":
    CLIChatInterface().run()
