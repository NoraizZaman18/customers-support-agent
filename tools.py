import json


# .....................search_faq() tool

def search_faq(userinput: str):
    try:
        with open("data/faq.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()

        for i in range(len(lines)):
            line = lines[i].strip()

            # Only check question lines
            if line.startswith("Q:"):

                # Keyword search (case-insensitive)
                if userinput.lower() in line.lower():

                    # Return the next line if it is an answer
                    if i + 1 < len(lines):
                        answer = lines[i + 1].strip()

                        if answer.startswith("A:"):
                            return answer.replace("A:", "").strip()

        return "No matching FAQ found."

    except FileNotFoundError:
        return "FAQ file not found."
    
# .......................check_return_policy()

def check_return_policy(userinput: str):
    try:
        with open("data/policy.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()

        query = userinput.lower()

        if "refund" in query:
            section = "REFUND POLICY"
        elif "return" in query:
            section = "RETURN POLICY"
        elif "exchange" in query:
            section = "EXCHANGE POLICY"
        elif "cancel" in query:
            section = "CANCELLATION POLICY"
        else:
            return "No matching policy found."

        collecting = False
        result = []

        for line in lines:
            line = line.strip()

            if line == section:
                collecting = True
                continue

            if collecting:
                if line.endswith("POLICY") and line != section:
                    break

                if line and not line.startswith("="):
                    result.append(line)

        if result:
            return "\n".join(result)

        return "Policy section not found."

    except FileNotFoundError:
        return "Policy file not found."
    

#.............check_order_status()


def check_order_status(order_id: str):
 try:
      with open("data/orders.json", "r") as file:
       orders = json.load(file)

      for order in orders:
          if order["order_id"] == order_id:
            return order
      return "order not found "           
 except FileNotFoundError:    
       return "file not found"
 

#...............calculate_refund()

 
def calculate_refund(order_id: str):
 try:
      with open("data/orders.json", "r") as file:
       orders = json.load(file)

      for order in orders:
          if order["order_id"] == order_id: 
            if order["status"]=="Returned":
              return order["price"]
            else: 
             return "This order is not eligible for a refund"
          
      return "order not found"            
 except FileNotFoundError:    
       return "file not found"   
 

#..................create_ticket()

def create_ticket(customer_name: str, issue: str):
    try:
        with open("data/tickets.json", "r", encoding="utf-8") as file:
               tickets = json.load(file)
               length = len(tickets)
               number = length + 1
               ticket_id = f"T{number:03d}"
               new_ticket = {
    "ticket_id": ticket_id,
    "customer_name": customer_name,
    "issue": issue,
    "status": "Open"
}
               
        tickets.append(new_ticket)

        with open("data/tickets.json", "w", encoding="utf-8") as file:
         json.dump(tickets, file)

        return f"Ticket created successfully. Ticket ID: {ticket_id}"
    except FileNotFoundError:
        return "File not found."
    


#  ............escalate_to_human()
def escalate_to_human(reason):
    return {
        "status": "escalated",
        "message": f"Your request has been escalated to a human support agent.",
        "reason": reason
    }