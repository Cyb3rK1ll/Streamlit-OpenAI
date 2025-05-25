import streamlit as st
import asyncio
import uuid
from agent import customer_service_agent, get_response  

# Display the title of the app and the options in the sidebar
with st.sidebar:
    st.title("Asistente de Soporte")

# Initialize variables in session state if they do not exist yet
if "chat_id" not in st.session_state:
    st.session_state.chat_id = uuid.uuid4().hex
st.sidebar.write(f"Chat ID: {st.session_state.chat_id}")

if "history" not in st.session_state:
    st.session_state.history = []  # Stores the conversation history

if "agent" not in st.session_state:
    st.session_state.agent = customer_service_agent  # Start with the customer service agent

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola, soy un asistente virtual 🤖. ¿Cómo puedo ayudarte?"}
    ]

# Display the message history in the chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Asynchronous function to handle user input
async def handle_user_input(prompt):
    # Add user message to Streamlit message history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call the asynchronous get_response function
    try:
        history = st.session_state.history
        agent, chat_id, history, final_output = await get_response(
            agent=st.session_state.agent,
            conversation_id=st.session_state.chat_id,
            history=history[:30],
            user_input=prompt,
        )

        # Update session state with new values
        st.session_state.agent = agent
        st.session_state.chat_id = chat_id
        st.session_state.history = history

        # Display the assistant's response
        with st.chat_message("assistant"):
            st.markdown(final_output)

        st.session_state.messages.append({"role": "assistant", "content": final_output})
    except Exception as e:
        st.error(f"Error: {e}")

# Function to run async tasks in Streamlit
def run_async(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(coroutine)
    loop.close()
    return result

# Capture user input
if prompt := st.chat_input("Type your message here..."):
    # Run the async function in a way compatible with Streamlit
    run_async(handle_user_input(prompt))
