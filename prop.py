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

# Store LLM generated responses
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

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
    # This function should use GPT-3.5 Turbo to generate an SQL query based on user input
    # You might need to use a specific prompt structure to guide the model in generating SQL queries
    # Example:
    prompt = f"Translate this request into an SQL query: '{user_input}'"
    response = openai.Completion.create(
        model="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=100
    )
    return response.choices[0].text.strip()

def format_query_results(query_results):
    # Format the SQL query results into a readable string
    formatted_results = "Here are the apartments I found:\n"
    for row in query_results:
        formatted_results += f"Apartment: {row[0]}, Location: {row[1]}, Price: {row[2]}\n"
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
