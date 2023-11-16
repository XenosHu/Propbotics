from llama_index.llms import OpenAI
from llama_index import VectorStoreIndex, SimpleDirectoryReader, SQLDatabase, ServiceContext
from sqlalchemy import select, create_engine, MetaData, Table, inspect, text
from llama_index.indices.struct_store.sql_query import NLSQLTableQueryEngine
from IPython.display import Markdown, display
import mysql.connector
from typing import Union, List
import streamlit as st
import openai
import os
import re

# App title
st.set_page_config(page_title="Property Finder")

config = {
    'user': 'propbotics',
    'password': 'Propbotics123',
    'host': 'chatbot.c0xmynwsxhmo.us-east-1.rds.amazonaws.com',
    'database': 'chatbot',
    'port': 3306
}

def engin_init(Config):
    connection = f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    engine = create_engine(connection)
    return engine

# OpenAI Credentials
with st.sidebar:
    openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
    if openai_api_key:
        try:
            # Directly set the API key in OpenAI configuration
            openai.api_key = openai_api_key

            st.success('API key accepted! You can now use the chatbot.', icon='✅')
        except Exception as e:
            st.error(f"Error with API key: {str(e)}")
    else:
        st.warning('Please enter your OpenAI API key!', icon='⚠️')


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]
if "logs" not in st.session_state:
    st.session_state.logs = []

def log_message(message):
    """Append a message to the log list."""
    st.session_state.logs.append(message)

def display_logs():
    """Display logs in Streamlit."""
    for log in st.session_state.logs:
        st.text(log)

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

def generate_gpt3_response(prompt_input,config):
    response_content = ""

    if "apartment" in prompt_input.lower():
    # Connect to the database and execute the query

        # connection = mysql.connector.connect(**config)
        connection = f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        engine = create_engine(connection)

        llm = OpenAI(temperature=0.5, model="gpt-3.5-turbo-16k")
        service_context = ServiceContext.from_defaults(llm=llm)
        sql_database = SQLDatabase(engine)
        
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        # Generate SQL query
        sql_query = chat_to_sql(prompt_input, sql_database, service_context)
        st.write("Raw query:", sql_query)
        # if sql_query and not sql_query.startswith("ERROR"):
        #     try:
        #         with engine.connect() as conn:
        #             result = conn.execute(text(sql_query))
        #             st.write(query_results)            # Execute the SQL query
        #             query_results = result.fetchall()      # Fetch all results
        #             # Format and display the results
        #             if query_results:
        #                 response_content = format_query_results(query_results)
        #             else:
        #                 response_content = "No results found."
        #     except Exception as e:
        #         response_content = f"SQL Execution Error: {e}"
        # else:
        #     response_content = "No valid SQL query generated."
        if sql_query and not sql_query.startswith("ERROR"):
            # Extract table name and check schema
            table_name = extract_table_name(sql_query)
            if table_name:
                columns = get_columns(table_name, config)
                try:
                    # Execute the SQL query
                    with engine.connect() as conn:
                        result = conn.execute(text(sql_query))
                        query_results = result.fetchall()
                        st.write("Raw query results:", query_results)
                        response_content = format_query_results(query_results)
                except SQLAlchemyError as e:
                    response_content = f"SQL Execution Error: {e}"
            else:
                response_content = "Could not determine the table from the query."
        else:
            response_content = "No valid SQL query generated."
    else:
        # Handle non-database queries
        response_content = get_gpt3_response(prompt_input)

    return response_content

    # cursor.close()
    # connection.close()

response_template = """
## Question

{question}

## Answer
```
{response}
```
## Generated SQL Query
```
{sql}
```
"""

# # Define chat_to_sql function
# def chat_to_sql(question, sql_database, service_context, tables=None, synthesize_response=True):
#     # table_name = extract_table_name(sql_query)
#     # columns = get_columns(table_name, config)
    
#     query_engine = NLSQLTableQueryEngine(
#         sql_database=sql_database,
#         tables=tables,
#         synthesize_response=synthesize_response,
#         service_context=service_context,
#     )
    
#     try:
#         response = query_engine.query(question)
#         sql = response.metadata["sql_query"]
#         return sql
#     except Exception as ex:
#         return f"ERROR: {str(ex)}"
#     display(Markdown(response_template.format(
#         question=question,
#         response=response_md,
#         sql=sql,
#     )))

def chat_to_sql(question, sql_database, service_context, synthesize_response=True):
    relevant_tables = determine_relevant_tables(question, config)

    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=relevant_tables,
        synthesize_response=synthesize_response,
        service_context=service_context,
    )
    
    try:
        response = query_engine.query(question)
        sql = response.metadata["sql_query"]
        return sql
    except Exception as ex:
        return f"ERROR: {str(ex)}"
    display(Markdown(response_template.format(
        question=question,
        response=response_md,
        sql=sql,
    )))
        
def determine_relevant_tables(question, config):
    # A basic and rudimentary mapping of keywords to table names
    keyword_to_table = {
        "apartment": "Building_test",  # Assuming questions about apartments map to the 'Building_test' table
        "unit": "Unit_test",           # Assuming questions about units map to the 'Unit_test' table
        # Add more mappings as needed
    }

    relevant_tables = []

    # Check if any keyword in the mapping is in the question
    for keyword, table in keyword_to_table.items():
        if keyword in question.lower():
            relevant_tables.append(table)

    # Return the list of relevant tables based on the question
    return relevant_tables
    
def extract_table_name(query):
    # A basic regex pattern for a simple SELECT query
    # This pattern assumes the query is well-formed and straightforward
    pattern = r"FROM\s+([a-zA-Z0-9_]+)"

    # Find matches in the query
    match = re.search(pattern, query, re.IGNORECASE)

    if match:
        # Return the first captured group (the table name)
        return match.group(1)
    else:
        return None

def get_columns(table_name, config):
    engine = engin_init(config)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table = metadata.tables[table_name]
    table_columns = []
    for column in table.columns:
        table_columns.append(column.name)
    return table_columns
    
def format_query_results(query_results):
    # Format the results into a readable format
    formatted_results = "Here are the results:\n"
    for row in query_results:
        formatted_results += f"{row}\n"
    return formatted_results

def get_gpt3_response(prompt_input):
    # Regular GPT-3.5 Turbo response handling
    conversation = [{"role": "system", "content": "You are a helpful assistant."}]
    for m in st.session_state.messages:
        conversation.append({"role": m["role"], "content": m["content"]})
    conversation.append({"role": "user", "content": prompt_input})

    gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation,
        max_tokens=300
    )
    return gpt_response.choices[0].message.content
    
# User-provided prompt

if prompt := st.chat_input(disabled=not openai_api_key):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = generate_gpt3_response(prompt,config)
                st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
