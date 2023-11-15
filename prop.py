import mysql.connector
import streamlit as st
import openai
import os

# App title
st.set_page_config(page_title="NYC Property Finder Chatbot")

# OpenAI Credentials
with st.sidebar:
    openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
    if openai_api_key:
        try:
            # Directly set the API key in OpenAI configuration
            openai.api_key = openai_api_key

            # Optionally, you can add a simple call here to validate the key
            # For example, a small request to the API and catch any exceptions

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


def generate_gpt3_response(prompt_input):
    # First, check if it's a database-related query
    if "apartment" in prompt_input.lower():
        # Generate SQL query using GPT-3.5 Turbo
        sql_query = generate_sql_query(prompt_input)
        
        # Connect to the database and execute the query
        config = {
            'user': 'propbotics',
            'password': 'Propbotics123',
            'host': 'chatbot.c0xmynwsxhmo.us-east-1.rds.amazonaws.com',
            'database': 'chatbot',
            'port': 3306
        }
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        cursor.execute(sql_query)
        query_results = cursor.fetchall()

        # Format and return the results
        response_content = format_query_results(query_results)
        

        cursor.close()
        connection.close()
    else:
        # Handle non-database queries
        response_content = get_gpt3_response(prompt_input)
        

    return response_content

def generate_sql_query(user_input):
    # Description of the database schema
    database_schema_info = (
        "The database has two tables: Building_test and Unit_test. "
        "Building_test includes BuildingID, Buildingname, website, location, address, description, building_image, postcode, and pet. "
        "Unit_test includes UnitID, building_id, unit number, rent_price, unit_type, unit image, floor_plan, availability, description, broker fee, and available date."
    )

    # Determine the context of the query
    if "apartment" in user_input.lower():
        # Context for searching an apartment
        table_context = "Generate an SQL query to find information from the Building_test table."
    elif "availability" in user_input.lower():
        # Context for checking availability
        table_context = "Generate an SQL query to find availability information from the Unit_test table."
    else:
        # General context
        table_context = "Generate an SQL query based on general information about buildings and units."

    # Updated prompt for GPT-3.5 Turbo
    prompt = f"Given the database structure: {database_schema_info}, and context: {table_context}, translate this user request into an SQL query: '{user_input}'"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    generated_sql = response.choices[0].message.content
    log_message(f"Generated SQL: {generated_sql}")

    return generated_sql
    
def format_query_results(query_results):
    # Format the SQL query results into a readable string
    formatted_results = "Here are the apartments I found:\n"
    for row in query_results:
        formatted_results += f"Apartment: {row[0]}, Location: {row[1]}, Price: {row[2]}\n"
    log_message(f"Generated SQL: {formatted_results}")
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

    # Generate a new response if last message is not from assistant
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = generate_gpt3_response(prompt)
                st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
