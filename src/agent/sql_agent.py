import os
import duckdb
import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.agent.llm_engine import LLMEngine
from src.agent.prompts import SYSTEM_PROMPT, REPORT_PROMPT, FIX_PROMPT

# Load environment variables
load_dotenv()

class SQLAgent:
    """
    The Orchestrator.
    This class takes a natural language question and converts it into SQL.
    """
    
    def __init__(self):
        # 0. Set our database path
        self.db_path = os.getenv("DB_PATH")
        
        if not self.db_path:
            raise ValueError("❌ DB_PATH not found in .env file!")

        # 1. Initialize our connection engine
        self.engine = LLMEngine()
        
        # 2. Setup the "Mad Libs" template
        # We define a 'system' role for rules and a 'user' role for the question
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{question}")
        ])
        
        # 3. Create a 'Chain'
        # This is a LangChain concept: Pipe the prompt into the LLM
        self.chain = self.prompt_template | self.engine.llm
        
        # 4. Setup the Reporting Chain
        self.report_prompt_template = ChatPromptTemplate.from_template(REPORT_PROMPT)
        self.report_chain = self.report_prompt_template | self.engine.llm
        
        # 5. Setup the Fix Chain
        self.fix_prompt_template = ChatPromptTemplate.from_template(FIX_PROMPT)
        self.fix_chain = self.fix_prompt_template | self.engine.llm

    def generate_sql(self, question: str, chat_history: list = None) -> str:
        """Translates the question into SQL code."""
        print(f"Agent is thinking about: '{question}'...")
        if chat_history is None:
            chat_history = []
        
        try:
            # We 'invoke' the chain, passing in the user's question and history
            response = self.chain.invoke({
                "question": question,
                "chat_history": chat_history
            })
            return response.content.strip()
        except Exception as e:
            return f"❌ SQL Generation Error: {str(e)}"

    def run_sql(self, sql: str):
        """
        The Hands.
        Executes the SQL code against our DuckDB database.
        """
        # If the SQL generation failed, don't try to run it
        if "❌" in sql:
            return sql
            
        try:
            # We use 'with' to ensure the connection closes automatically
            with duckdb.connect(self.db_path) as con:
                results_df = con.execute(sql).df()
                return results_df
        except Exception as e:
            return f"❌ Database Execution Error: {str(e)}"

    def fix_sql(self, question: str, broken_sql: str, error_msg: str) -> str:
        """The Debugger. Asks the AI to fix its own broken SQL."""
        print(f" Attempting to self-correct SQL (Error: {error_msg.split(':')[0]}...)")
        try:
            response = self.fix_chain.invoke({
                "question": question,
                "broken_sql": broken_sql,
                "error_message": error_msg
            })
            return response.content.strip()
        except Exception as e:
            return f"❌ Fix Generation Error: {str(e)}"

    def ask(self, question: str, chat_history: list = None, max_retries: int = 3) -> str:
        """The Complete Loop: Question -> SQL -> Data -> Answer."""
        # 1. Generate the 'Ticket' (SQL)
        sql = self.generate_sql(question, chat_history)
        
        results = None
        
        # 2. Execute on 'Kitchen' (DuckDB) with Self-Correction Loop
        for attempt in range(max_retries):
            results_df = self.run_sql(sql)
            
            # Check if execution was successful
            # run_sql returns a DataFrame on success, or a string starting with ❌ on failure
            if isinstance(results_df, pd.DataFrame):
                # Success! Break out of the loop
                break
                
            # If we get here, results_df is an error string
            print(f"⚠️ SQL Error caught on attempt {attempt + 1}.")
            
            if attempt < max_retries - 1:
                # Ask AI to fix the SQL
                sql = self.fix_sql(question, sql, results_df)
            else:
                # We failed after max retries
                return f"Sorry, I couldn't generate a valid query after {max_retries} attempts. Last error: {results_df}", None
        
        # 3. Get the 'Voice' (Report)
        # We invoke our second chain, passing in all the context
        try:
            results_str = results_df.to_markdown() if not results_df.empty else "No results found."
            response = self.report_chain.invoke({
                "question": question,
                "sql": sql,
                "results": results_str
            })
            return response.content.strip(), results_df
        except Exception as e:
            return f"❌ Reporting Error: {str(e)}", None

if __name__ == "__main__":
    # Quick test drive!
    agent = SQLAgent()
    
    test_question = "What is the total sales volume for Studios in JVC from 2022?"
    report, df = agent.ask(test_question, chat_history=[])
    
    print("\n--- FINAL ANSWER ---")
    print(report)
    print("\n--- DATAFRAME ---")
    print(df)
    print("----------------------")
