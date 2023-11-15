import streamlit as st
import openai
import os

# App title
st.set_page_config(page_title="NYC Property Finder Chatbot")

# OpenAI Credentials
with st.sidebar:
    openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
    if openai_api_key:
        st.success('API key accepted! You can now use the chatbot.', icon='✅')
        os.environ['OPENAI_API_KEY'] = openai_api_key
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

# Function for generating GPT-3.5 Turbo response
def generate_gpt3_response(prompt_input):
    conversation = "\n".join([m["content"] for m in st.session_state.messages])
    prompt = f"{conversation}\n{prompt_input}"
    response = openai.Completion.create(
        model="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=150,
        temperature=0.7,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].text.strip()

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
