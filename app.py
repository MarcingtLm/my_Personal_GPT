import json
from pathlib import Path
import streamlit as st
from openai import OpenAI
import requests
import os
import hashlib

def get_api_key_securely():
    if "api_key_verified" not in st.session_state:
        st.session_state["api_key_verified"] = False

    if not st.session_state["api_key_verified"]:
        api_key = st.text_input(
            "Wklej swój klucz API OpenAI ",
            type="password",
            placeholder="sk-…",
            key="raw_api_key"
        )
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                client.models.list()

                # Generujemy user_id na podstawie klucza API
                user_id = hashlib.md5(api_key.encode('utf-8')).hexdigest()
                st.session_state["openai_api_key"] = api_key
                st.session_state["user_id"] = user_id
                st.session_state["api_key_verified"] = True
                st.rerun()
            except Exception:
                st.error("Nieprawidłowy klucz API")
        st.stop()
    return st.session_state["openai_api_key"]

def get_usd_to_pln():
    url = "https://api.nbp.pl/api/exchangerates/rates/A/USD/?format=json"
    response = requests.get(url)
    data = response.json()
    return data["rates"][0]["mid"]

model_pricings = {
    "gpt-4o": {
        "input_tokens": 5.00 / 1_000_000,  # per token
        "output_tokens": 15.00 / 1_000_000,  # per token
    },
    "gpt-4o-mini": {
        "input_tokens": 0.150 / 1_000_000,  # per token
        "output_tokens": 0.600 / 1_000_000,  # per token
    },
    "gpt-5": {
        "input_tokens": 1.250 / 1_000_000,  # per token
        "output_tokens": 10.000 / 1_000_000,  # per token
    },
    "gpt-5-mini": {
        "input_tokens": 0.250 / 1_000_000,  # per token
        "output_tokens": 2.000 / 1_000_000,  # per token
    },
    "gpt-5-nano": {
        "input_tokens": 0.050 / 1_000_000,  # per token
        "output_tokens": 0.400 / 1_000_000,  # per token
    }
}

api_key = get_api_key_securely()
openai_client = OpenAI(api_key=api_key)

# Obsługa ścieżek usera
DB_PATH = Path("db")

def get_user_db_paths():
    # user_id wygenerowany jest przy logowaniu (MD5 z API Key)
    user_id = st.session_state.get("user_id", "default")
    user_db_path = DB_PATH / user_id
    user_conversations_path = user_db_path / "conversations"
    return user_db_path, user_conversations_path

#
# CHATBOT
#
def chatbot_reply(user_prompt, memory):
    messages = [
        {
            "role": "system",
            "content": st.session_state["chatbot_personality"],
        },
    ]
    for message in memory:
        messages.append({"role": message["role"], "content": message["content"]})

    messages.append({"role": "user", "content": user_prompt})

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    usage = {}
    if response.usage:
        usage = {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "role": "assistant",
        "content": response.choices[0].message.content,
        "usage": usage,
    }

#
# CONVERSATION HISTORY AND DATABASE
#
DEFAULT_PERSONALITY = """
Jesteś pomocnikiem, który odpowiada na wszystkie pytania użytkownika.
Odpowiadaj na pytania w sposób zwięzły i zrozumiały.
""".strip()

DEFAULT_MODEL = "gpt-4o"

def load_conversation_to_state(conversation):
    st.session_state["id"] = conversation["id"]
    st.session_state["name"] = conversation["name"]
    st.session_state["messages"] = conversation["messages"]
    st.session_state["chatbot_personality"] = conversation["chatbot_personality"]
    st.session_state["MODEL"] = conversation.get("model", DEFAULT_MODEL)

def load_current_conversation():
    user_db_path, user_conversations_path = get_user_db_paths()
    
    if not user_db_path.exists():
        user_db_path.mkdir(parents=True, exist_ok=True)
        user_conversations_path.mkdir(exist_ok=True)
        conversation_id = 1
        conversation = {
            "id": conversation_id,
            "name": "Konwersacja 1",
            "chatbot_personality": DEFAULT_PERSONALITY,
            "messages": [],
        }
        with open(user_conversations_path / f"{conversation_id}.json", "w") as f:
            f.write(json.dumps(conversation))
        with open(user_db_path / "current.json", "w") as f:
            f.write(json.dumps({
                "current_conversation_id": conversation_id,
            }))
    else:
        with open(user_db_path / "current.json", "r") as f:
            data = json.loads(f.read())
            conversation_id = data["current_conversation_id"]
        with open(user_conversations_path / f"{conversation_id}.json", "r") as f:
            conversation = json.loads(f.read())

    load_conversation_to_state(conversation)

def save_current_conversation_messages():
    user_db_path, user_conversations_path = get_user_db_paths()
    conversation_id = st.session_state["id"]
    new_messages = st.session_state["messages"]
    with open(user_conversations_path / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read())
    with open(user_conversations_path / f"{conversation_id}.json", "w") as f:
        f.write(json.dumps({
            **conversation,
            "messages": new_messages,
        }))

def save_current_conversation_name():
    user_db_path, user_conversations_path = get_user_db_paths()
    conversation_id = st.session_state["id"]
    new_conversation_name = st.session_state["new_conversation_name"]
    with open(user_conversations_path / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read())
    with open(user_conversations_path / f"{conversation_id}.json", "w") as f:
        f.write(json.dumps({
            **conversation,
            "name": new_conversation_name,
        }))

def save_current_conversation_personality():
    user_db_path, user_conversations_path = get_user_db_paths()
    conversation_id = st.session_state["id"]
    new_chatbot_personality = st.session_state["new_chatbot_personality"]
    with open(user_conversations_path / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read())
    with open(user_conversations_path / f"{conversation_id}.json", "w") as f:
        f.write(json.dumps({
            **conversation,
            "chatbot_personality": new_chatbot_personality,
        }))

def save_current_conversation_model():
    user_db_path, user_conversations_path = get_user_db_paths()
    conversation_id = st.session_state["id"]
    new_model = st.session_state["MODEL"]
    with open(user_conversations_path / f"{conversation_id}.json", "r") as f:
        conversation = json.load(f)
    conversation["model"] = new_model
    with open(user_conversations_path / f"{conversation_id}.json", "w") as f:
        json.dump(conversation, f)

def create_new_conversation():
    user_db_path, user_conversations_path = get_user_db_paths()
    conversation_ids = []
    for p in user_conversations_path.glob("*.json"):
        conversation_ids.append(int(p.stem))
    conversation_id = max(conversation_ids) + 1 if conversation_ids else 1
    personality = DEFAULT_PERSONALITY
    if "chatbot_personality" in st.session_state and st.session_state["chatbot_personality"]:
        personality = st.session_state["chatbot_personality"]
    conversation = {
        "id": conversation_id,
        "name": f"Konwersacja {conversation_id}",
        "chatbot_personality": personality,
        "model": DEFAULT_MODEL, 
        "messages": [],
    }
    if not user_conversations_path.exists():
        user_conversations_path.mkdir(parents=True, exist_ok=True)
    with open(user_conversations_path / f"{conversation_id}.json", "w") as f:
        f.write(json.dumps(conversation))
    with open(user_db_path / "current.json", "w") as f:
        f.write(json.dumps({
            "current_conversation_id": conversation_id,
        }))
    load_conversation_to_state(conversation)
    st.rerun()

def switch_conversation(conversation_id):
    user_db_path, user_conversations_path = get_user_db_paths()
    with open(user_conversations_path / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read())
    with open(user_db_path / "current.json", "w") as f:
        f.write(json.dumps({
            "current_conversation_id": conversation_id,
        }))
    load_conversation_to_state(conversation)
    st.rerun()

def list_conversations():
    user_db_path, user_conversations_path = get_user_db_paths()
    conversations = []
    if user_conversations_path.exists():
        for p in user_conversations_path.glob("*.json"):
            with open(p, "r") as f:
                conversation = json.loads(f.read())
                conversations.append({
                    "id": conversation["id"],
                    "name": conversation["name"],
                })
    return conversations

def safe_delete_conversation(conversation_id):
    user_db_path, user_conversations_path = get_user_db_paths()
    conversations = list_conversations()
    if len(conversations) <= 1:
        st.error("Nie można usunąć ostatniej konwersacji!")
        return False
    if conversation_id == st.session_state["id"]:
        st.error("Nie można usunąć aktualnie otwartej konwersacji!")
        return False
    conversation_file = user_conversations_path / f"{conversation_id}.json"
    if conversation_file.exists():
        os.remove(conversation_file)
        st.rerun()
        return True
    else:
        st.error("Konwersacja nie istnieje!")

def display_conversation_row(conversation):
    c0, c1, c2 = st.columns([8, 2, 2])
    with c0:
        st.write(conversation["name"])
    with c1:
        is_current = conversation["id"] == st.session_state["id"]
        if st.button("załaduj", 
                    key=f"load_conv_{conversation['id']}", 
                    disabled=is_current,
                    use_container_width=True):
            switch_conversation(conversation["id"])
    with c2:
        conversations_count = len(list_conversations())
        can_delete = not is_current and conversations_count > 1
        if st.button("usuń", 
                    key=f"delete_conv_{conversation['id']}", 
                    disabled=not can_delete,
                    use_container_width=True):
            safe_delete_conversation(conversation["id"])

# MAIN PROGRAM
load_current_conversation()

st.set_page_config(page_title="Personal GPT", layout="centered")

available_models = list(model_pricings.keys())

if "MODEL" not in st.session_state:
    st.session_state["MODEL"] = DEFAULT_MODEL

selected_model = st.sidebar.selectbox(
    "Zmień model Ai ( domyślnie ustawiony GPT-4o )",
    options=available_models,
    index=available_models.index(st.session_state["MODEL"]),
    key="model_selector"
)

if st.sidebar.button("Zapisz model"):
    if selected_model != st.session_state["MODEL"]:
        st.session_state["MODEL"] = selected_model
        save_current_conversation_model()
        st.rerun()

MODEL = st.session_state["MODEL"]
PRICING = model_pricings[MODEL]
USD_TO_PLN = get_usd_to_pln()

st.title("🧠🌐 MyPersonal GPT -> 🎓🚀")

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("O co chcesz spytać?")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        response = chatbot_reply(prompt, memory=st.session_state["messages"][-20:])
        st.markdown(response["content"])
    st.session_state["messages"].append({"role": "assistant", "content": response["content"], "usage": response["usage"],"model": MODEL})
    save_current_conversation_messages()

with st.sidebar:
    st.text(f"Aktualny model Ai : {MODEL}")
    st.markdown(
        f"Aktualna konwersacja :  <span style='font-weight:bold; color:green;'>{st.session_state['name']}</span>",
        unsafe_allow_html=True
    )

    total_cost_current_model = 0
    total_cost_all_models = 0

    for message in st.session_state.get("messages") or []:
        if "usage" in message:
            model = message.get("model", st.session_state.get("MODEL", DEFAULT_MODEL))
            pricing = model_pricings.get(model, model_pricings[DEFAULT_MODEL])

            msg_cost = (
                message["usage"]["prompt_tokens"] * pricing["input_tokens"] +
                message["usage"]["completion_tokens"] * pricing["output_tokens"]
            )
            total_cost_all_models += msg_cost

            if model == st.session_state["MODEL"]:
                total_cost_current_model += msg_cost

    c0, c1 = st.columns(2)
    with c0:
        st.metric("Koszt rozmowy (USD)", f"${total_cost_current_model:.4f}")
    with c1:
        st.metric("Koszt rozmowy (PLN)", f"{total_cost_current_model * USD_TO_PLN:.4f}")

    st.markdown(
        f"**Całkowity koszt tej konwersacji (wszystkie modele): "
        f"${total_cost_all_models:.4f} / {total_cost_all_models * USD_TO_PLN:.4f} PLN**"
    )

    st.session_state["name"] = st.text_input(
        " Dodaj nazwę rozmowy",
        value=st.session_state["name"],
        key="new_conversation_name",
        on_change=save_current_conversation_name,
    )
    st.session_state["chatbot_personality"] = st.text_area(
        " Opisz osobowość chatbota",
        max_chars=1000,
        height=200,
        value=st.session_state["chatbot_personality"],
        key="new_chatbot_personality",
        on_change=save_current_conversation_personality,
    )

    c0, c1 = st.columns([3, 1])
    with c0:
        st.subheader("Zapisane rozmowy")
    with c1:
        if st.button("Dodaj chat ", use_container_width=True):
            create_new_conversation()

    conversations = list_conversations()  
    sorted_conversations = sorted(conversations, key=lambda x: x["id"], reverse=True)
    if sorted_conversations:
        for conversation in sorted_conversations[:7]:
            display_conversation_row(conversation)
    else:   
        st.info("Brak zapisanych rozmów")
