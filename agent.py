# Step 1 - Zaroori imports
# prompts.py se system prompt import ho raha hai (agent ka main instruction set)
from prompts import SYSTEM_PROMPT_V1_3

# Groq client aur uske specific error types import ho rahe hain
from groq import Groq

# .env file se environment variables load karne ke liye
from dotenv import load_dotenv
import os

# JSON data ko parse/convert karne ke liye (Python dict <-> JSON string)
import json

# Pydantic model jo LLM ke final response ko validate karega
from models import AgentResponse

# Prompt injection check karne wala function (security layer)
from validator import is_prompt_injection

# Saare tools import ho rahe hain jo agent use karega
from tools import (
    search_faq,
    check_return_policy,
    check_order_status,
    calculate_refund,
    create_ticket,
    escalate_to_human
)

# Step 2 - .env file load ho rahi hai
# Isse GROQ_API_KEY environment variable mein aa jaayegi
load_dotenv()

# Step 3 - API key nikal rahe hain environment se
api_key = os.getenv("GROQ_API_KEY")

# Step 4 - Groq client banaya, ye client hi LLM se baat karega
client = Groq(
    api_key=api_key
)


# Step 5 - Python dictionary jo tool ka naam (string) -> asal Python function map karti hai
# Jab LLM kahega "check_order_status" call karo, hum is dictionary se
# asal function nikal ke run karenge
TOOLS = {
    "check_order_status": check_order_status,
    "search_faq": search_faq,
    "check_return_policy": check_return_policy,
    "calculate_refund": calculate_refund,
    "create_ticket": create_ticket,
    "escalate_to_human": escalate_to_human
}


# Step 6 - Ye wo list hai jo LLM ko dikhai jaati hai
# Isme sirf tools ka "schema" hai (naam, description, required parameters)
# Ye list khud koi tool RUN nahi karti, sirf LLM ko batati hai
# ke kaunse tools available hain aur unko kaise call karna hai
LLM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_order_status",
            "description": "Checks the status and details of a customer order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The customer's order ID."
                    }
                },
                "required": ["order_id"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": "Searches the FAQ file to answer customer questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "userinput": {
                        "type": "string",
                        "description": "The customer's question."
                    }
                },
                "required": ["userinput"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "check_return_policy",
            "description": "Checks the return and refund policy from the policy file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "userinput": {
                        "type": "string",
                        "description": "The customer's policy question."
                    }
                },
                "required": ["userinput"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "calculate_refund",
            "description": "Calculates refund amount for a returned order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The customer's order ID."
                    }
                },
                "required": ["order_id"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Creates a support ticket for customer issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Customer name."
                    },
                    "issue": {
                        "type": "string",
                        "description": "Customer problem."
                    }
                },
                "required": [
                    "customer_name",
                    "issue"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalates difficult cases to a human agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for escalation."
                    }
                },
                "required": ["reason"]
            }
        }
    }
]


# =====================================================
# PROMPT CHAIN - PART 1: CLASSIFICATION
# =====================================================

def classify_request(user_input: str):
    """
    Ye function pehla step hai poore prompt chain ka.
    Iska sirf ek kaam hai: user ka message padh kar
    ye decide karna ke ye kis category mein aata hai
    (order_status, refund, faq, wagera).

    Ye khud koi tool call nahi karta, sirf classification karta hai.
    """

    # Step 1 - LLM ko diya jaane wala system instruction
    # Isme LLM ko clearly bataya gaya hai ke sirf JSON return karo,
    # aur kaunsi category kis situation mein use honi chahiye
    classification_prompt = """
You are a customer support classifier.

Your ONLY job is to classify the user's request.

Choose exactly ONE category from:

- order_status
- refund
- return_policy
- faq
- ticket
- escalation

Rules:

- If the customer asks where their order is, use:
  order_status

- If the customer wants money back for an order, use:
  refund

- If the customer asks about return rules, damaged products,
  exchange policy, refund policy, or return window, use:
  return_policy

- If the customer asks general questions about shipping,
  payment, warranty, products, or other information, use:
  faq

- If the customer wants to create a complaint/support request,
  use:
  ticket

- If the customer asks for a manager or human agent, use:
  escalation

Return ONLY JSON.

Example:

{
    "category": "return_policy"
}
"""

    # Step 2 - Ye call actual LLM ko jaati hai
    # Hum yahan system prompt (rules) + user ka asal message
    # dono ek "messages" list mein bhej rahe hain
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": classification_prompt
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    # Step 3 - LLM ka jawab abhi ek JSON-shaped STRING hai
    # Python object nahi, sirf text hai jisme JSON likha hua hai
    # Example: '{"category":"order_status"}'
    result = response.choices[0].message.content

    # Step 4 - Is JSON string ko asal Python dictionary mein convert kar rahe hain
    # Ab hum "category" key ko normal Python dict ki tarah access kar sakte hain
    classification = json.loads(result)

    # Step 5 - Sirf category value wapas bhej rahe hain (jaise "refund")
    return classification["category"]


# =====================================================
# PROMPT CHAIN - PART 2: GATHER MISSING INFORMATION
# =====================================================

def gather_information(category: str, user_input: str):
    """
    Ye prompt chain ka doosra step hai.
    Classification ke baad, ye function check karta hai ke
    us category ko process karne ke liye koi zaroori
    information missing to nahi (jaise order_id, customer_name).
    """

    # Step 1 - Dynamic prompt banaya ja raha hai
    # Notice: category variable ko f-string ke zariye
    # seedha prompt ke andar daala gaya hai
    gather_prompt = f"""
You help determine what information is missing before a customer support request can be processed.

The request category is:

{category}

Rules:

1. If category == "order_status"
   Required:
   - order_id

2. If category == "refund"
   Required:
   - order_id

3. If category == "faq"
   Required:
   - nothing

4. If category == "return_policy"
   Required:
   - nothing

5. If category == "ticket"
   Required:
   - customer_name
   - issue

6. If category == "escalation"
   Required:
   - nothing
   The user's message itself is enough to use as the escalation reason.

Only return fields that are actually missing from the user's message.

Return ONLY valid JSON.

Example 1:

{{
    "missing": ["order_id"]
}}

Example 2:

{{
    "missing": ["customer_name"]
}}

Example 3:

{{
    "missing": []
}}
"""

    # Step 2 - Ye call LLM ko jaati hai
    # Hum ek Python list of dictionaries bhej rahe hain (messages)
    # Groq SDK khud isse JSON mein convert kar ke API ko bhejta hai,
    # kyunke LLM sirf JSON samajhta hai, Python object nahi.
    #
    # Jo request actual bheji jaati hai wo kuch aise dikhti hai (background mein):
    #
    # {
    #   "model": "llama-3.3-70b-versatile",
    #   "messages": [
    #       {"role": "system", "content": "..."},
    #       {"role": "user", "content": "Where is my order ORD1001?"}
    #   ]
    # }
    #
    # LLM andar hi andar decide karta hai category/missing fields,
    # aur wapas bhi JSON hi bhejta hai, jaise:
    #
    # {
    #   "choices": [
    #       { "message": { "content": "{\"missing\": []}" } }
    #   ]
    # }
    #
    # Groq SDK is poori JSON response ko ek Python object mein convert kar deta hai
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": gather_prompt
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    # Step 3 - response.choices[0].message.content abhi bhi ek STRING hai
    # jisme JSON likha hua hai, jaise: '{"missing": []}'
    result = response.choices[0].message.content

    # Step 4 - Is JSON string ko real Python dictionary mein convert kiya
    # '{"missing": []}'  ->  {"missing": []}
    data = json.loads(result)

    # Step 5 - "missing" list wapas bhej rahe hain (empty ya filled)
    return data["missing"]


# =====================================================
# PROMPT CHAIN KHATAM - AB DATA ASAL AGENT (ReAct LOOP) KO JAATA HAI
# =====================================================

import re
from groq import BadRequestError


def ask_llm(messages: list):
    """
    Ye asal "agent brain" hai - ReAct loop.
    Ye function baar baar (while True) LLM ko call karta hai:
    1. LLM decide karta hai koi tool chahiye ya nahi
    2. Agar tool chahiye, hum wo tool run karte hain
    3. Result LLM ko wapas dete hain
    4. LLM phir se sochta hai (loop continue hota hai)
    5. Jab LLM final answer de deta hai, loop return kar deta hai
    """

    # Step 1 - Infinite loop shuru, jab tak final answer na mil jaaye
    while True:

        try:
            # Step 2 - Poori conversation history + available tools
            # LLM ko bheji ja rahi hai
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=LLM_TOOLS
            )

        except BadRequestError as e:
            # Step 2a - Kabhi kabhi model apna final JSON answer
            # ek "fake tool call" (jaise "json" ya "JSON" naam ka tool)
            # ke andar wrap kar deta hai, jo Groq API reject kar deta hai
            # request level par hi - is wajah se hum response object
            # milne se pehle hi crash ho jaate the.
            #
            # Is except block mein hum error ke andar se hi
            # asal JSON data nikaal ke recover karne ki koshish karte hain.
            error_body = e.response.json()
            failed_generation = error_body["error"].get("failed_generation")

            if failed_generation:
                try:
                    # Step 2b - Error ke andar chupi hui JSON string
                    # ko parse kar rahe hain
                    fake_call = json.loads(failed_generation)
                    arguments = fake_call["arguments"]

                    # Step 2c - Is data ko humare AgentResponse model
                    # ke against validate kar rahe hain
                    validated_response = AgentResponse.model_validate(arguments)

                    # Step 2d - Ise conversation history mein normal
                    # assistant message ki tarah save kar rahe hain
                    messages.append({
                        "role": "assistant",
                        "content": json.dumps(arguments)
                    })

                    # Step 2e - Recovered valid response wapas bhej rahe hain
                    return validated_response

                except Exception as inner_e:
                    print("Validation Error (recovered fake tool case):", inner_e)
                    return None

            # Step 2f - Agar failed_generation bhi nahi mila,
            # to koi aur hi API error hai jo hum recover nahi kar sakte
            print("Unhandled API error:", e)
            return None

        # Step 3 - Agar koi crash nahi hua, to LLM ka message nikaal rahe hain
        message = response.choices[0].message

        # Step 4 - Check kar rahe hain ke LLM ne koi tool maanga ya nahi
        #
        # Agar LLM tool chahta hai, response kuch aisa dikhta hai:
        # {
        #     "tool_calls": [
        #         {
        #             "function": {
        #                 "name": "check_order_status",
        #                 "arguments": "{\"order_id\":\"ORD1001\"}"
        #             }
        #         }
        #     ]
        # }
        if message.tool_calls:

            # Step 5 - Sirf pehla tool call le rahe hain
            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name

            # Step 6 - Arguments abhi JSON string hain,
            # inko Python dictionary mein convert kar rahe hain
            # Example: '{"order_id":"ORD1001"}' -> {"order_id": "ORD1001"}
            arguments = json.loads(tool_call.function.arguments)

            # Step 7 - Agar model ne koi aisa tool call kiya jo
            # humari TOOLS dictionary mein exist hi nahi karta
            # (jaise fake "json" tool), to ye us JSON ko hi
            # final answer maan kar validate karne ki koshish karte hain
            if tool_name not in TOOLS:

                try:
                    validated_response = AgentResponse.model_validate(arguments)
                    messages.append({
                        "role": "assistant",
                        "content": json.dumps(arguments)
                    })
                    return validated_response
                except Exception as e:
                    print("Validation Error (fake tool case):", e)
                    return None

            # Step 8 - Asal tool case: dictionary se real Python function nikala
            # tool_name = "check_order_status" hai to
            # tool_function ban jaata hai check_order_status function
            tool_function = TOOLS[tool_name]

            # Step 9 - Tool ko run kar rahe hain, arguments ko
            # keyword arguments ki tarah unpack kar ke (**arguments)
            #
            # Ye pure normal Python hai - yahan koi AI involved nahi.
            # Suppose result mil jaata hai:
            # {"status": "Delivered", "product": "Wireless Mouse"}
            result = tool_function(**arguments)

            # Step 10 - LLM ka tool-request wala message conversation
            # history mein save kar rahe hain, taake agli baar
            # jab hum poori history LLM ko bhejenge, usse pata ho
            # ke usne pehle kya maanga tha
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                ]
            })

            # Step 11 - Tool ka result wapas LLM ko dene ke liye
            # conversation mein "tool" role ke saath save kar rahe hain
            #
            # json.dumps() isliye use kiya kyunke result Python dictionary hai,
            # aur LLM ko sirf JSON text samajh aata hai, Python object nahi
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

            # Step 12 - Loop ke start mein wapas jaate hain,
            # taake LLM tool ka result dekh kar dobara soche
            continue

        else:
            # Step 13 - Is else block mein aane ka matlab:
            # LLM ne koi tool nahi maanga, matlab ye uska
            # FINAL answer hai (plain text content ki shakal mein)
            llm_output = message.content

            try:
                # Step 14 - Is text ko humare AgentResponse Pydantic
                # model ke against validate kar rahe hain
                # (check kar rahe hain ke sahi JSON structure hai ya nahi)
                validated_response = AgentResponse.model_validate_json(llm_output)

                # Step 15 - Valid response ko conversation history
                # mein bhi save kar rahe hain
                messages.append({
                    "role": "assistant",
                    "content": llm_output
                })

                # Step 16 - Validated, structured response wapas bhej rahe hain
                return validated_response

            except Exception as e:
                # Step 17 - Agar JSON invalid nikla (malformed, empty, etc)
                # to error print kar ke None return kar rahe hain
                print("Validation Error:", e)
                return None


# =====================================================
# MAIN PROGRAM - MULTI-TURN CONVERSATION LOOP
# =====================================================

if __name__ == "__main__":

    # Step 1 - Conversation history shuru ho rahi hai
    # Sabse pehla message hamesha "system" role ka hota hai,
    # jo agent ke behaviour rules define karta hai
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_V1_3
        }
    ]

    # Step 2 - Ye loop tab tak chalta rahega jab tak user "exit" na likhe
    while True:

        # Step 3 - User se input le rahe hain
        user_input = input("User: ")

        # Step 4 - Agar user exit likhe, loop break kar ke
        # program khatam kar dete hain
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        # Step 5 - Prompt injection check - security layer
        # Agar user koi aisi cheez likhe jo system prompt ko
        # bypass/reveal karne ki koshish ho, to hum request
        # ko yahin rok dete hain, aage LLM tak jaane hi nahi dete
        if is_prompt_injection(user_input):
            print("I'm sorry, but I can't comply with requests that attempt to bypass or reveal my instructions.")
            continue

        # Step 6 - User ka message conversation history mein add kar rahe hain
        messages.append(
            {
                "role": "user",
                "content": user_input
            }
        )

        # Step 7 - PROMPT CHAIN STEP 1: request classify ki ja rahi hai
        # (order_status, refund, faq, wagera)
        category = classify_request(user_input)

        # Step 8 - PROMPT CHAIN STEP 2: check kar rahe hain ke
        # koi zaroori information missing to nahi
        missing = gather_information(category, user_input)

        # Step 9 - Debugging ke liye category aur missing fields print
        print("Category:", category)
        print("Missing:", missing)

        # Step 10 - Agar kuch missing hai, to LLM/tools ko call
        # kiye baghair hi user se wo cheez maang lete hain
        if missing:

            print(
                f"I still need: {', '.join(missing)}"
            )

        else:

            # Step 11 - Sab kuch available hai, ab asal ReAct
            # agent loop chalate hain jo tools bhi use kar sakta hai
            answer = ask_llm(messages)

            # Step 12 - Agar valid answer mila, customer ko dikhate hain
            if answer:
                print(answer.final_answer)

    # Step 13 - Program exit hone se pehle, poori conversation
    # history ko ek JSON file mein save kar rahe hain,
    # taake baad mein dekh sakein kya kya baat hui thi
    with open("conversation_log.json", "w") as f:
        json.dump(messages, f, indent=4)
