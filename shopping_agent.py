from typing import Optional
import json
import sqlite3
import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from reviews_api import get_product_reviews, get_ratings_for_products
import base64

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

llm=ChatAnthropic(model="claude-opus-4-8")
vision_llm = ChatAnthropic(model="claude-haiku-4-5-20251001")

@tool
def search_products(query: str, max_price: Optional[float] = None, is_organic: Optional[bool]=None) -> str:
   """
   Search the product database by keyword (matched against name, description and catergory).
   Optionally filter by max price and whether the product is organic.
   Returns a JSON array of matching products, each with: id, name, description, category, price, is_organic.
   """

   conn = sqlite3.connect(DB_PATH)
   cursor = conn.cursor()

   sql="SELECT id, name, description, category, price, is_organic FROM products WHERE 1=1"
   params: list = []

   if query:
         sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
         like = f"%{query}%"
         params.extend([like, like, like])

   if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)

   if is_organic is not None:
        sql += " AND is_organic = ?"
        params.append(1 if is_organic else 0)
    
   cursor.execute(sql, params)
   results = cursor.fetchall()
   conn.close()

   products = [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "category": row[3],
            "price": row[4],
            "is_organic": bool(row[5])
        }
        for row in results
    ]
   return json.dumps(products)

@tool
def checkout(product_id: int) -> str:
     """
     Place an order dor the given product id. Saves the order to the database and returnms 
     a confirmation message with the order ID, product name, and price.
     """

     conn = sqlite3.connect(DB_PATH)
     cursor = conn.cursor()
     cursor.execute("SELECT name, price FROM products WHERE id = ?", (product_id,))
     row= cursor.fetchone()

     if not row:
          conn.close()
          return f"Product with id {product_id} not found."
     
     name, price = row
     cursor.execute(
          "INSERT INTO orders (product_id, product_name, price) VALUES (?, ?, ?)", (product_id, name, price)
          )
     order_id = cursor.lastrowid
     conn.commit()
     conn.close()

     return (
          f"Order {order_id} confirmed! {name} has been successfully ordered for ${price:.2f}."
          f"Your order will arrive in 3-5 business days. Thank you for shopping with us!")


@tool
def describe_product_image(image_path: str) -> str:
     """
     Analyze the product image using the vision-capable LLM and return a description of the product, including any visible details that may not be in the text database.
     Use this when the user uploads a photo of a product they are interested in.
     Uses the vision-capable LLM to analyze the product image and return a description of the product, including any visible details that may not be in the text database.
     The return atttributes can be used directly with search_products.
     """
     with open(image_path, "rb") as f:
          image_data = base64.b64encode(f.read()).decode()

     with open(image_path, "rb") as f:
          header = f.read(12)
     if header[:4] == b'\x89PNG':
          mime = "image/png"
     elif header[:2] == b'\xff\xd8':
          mime = "image/jpeg"
     elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
          mime = "image/webp"
     elif header[:6] in (b'GIF87a', b'GIF89a'):
          mime = "image/gif"
     else:
          ext = os.path.splitext(image_path)[1].lower().lstrip(".")
          mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

     message = HumanMessage(content=[
            {
                 "type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{image_data}"}
            },
            {
                    "type": "text",
                    "text": (
                         "Describe the product in this image, including any visible details that may not be in the text database. Provide attributes that can be used with the search_products tool."
                         "Look at the product image and extract its key attributes."
                         "RETURN ONLY a JSON OBJECT with the following fields:\n"
                         "- product_type: the type of product (e.g. 'honey', 'olive oil', 'almonds')\n"
                         "- search_query: a short keyword or phrase that can be used to search for it (e.g 'honey', 'extra virgin olive oil', 'raw almonds')\n"
                         "- is_organic: true if the label says organic, false. if not, null if unclear\n"
                         "- description: one sentence describing the product\n"
                    ),
                    },
     ])

     response = vision_llm.invoke([message])
     return response.content



#-----------------------------------------------------------------------------------------------------------
# Agent
#-----------------------------------------------------------------------------------------------------------

agent = create_agent(
     tools=[search_products, get_ratings_for_products, checkout, describe_product_image], 
     model=llm,
     system_prompt=(
    "You are a helpful shopping assistant. Follow these rules strictly.\n\n"

    "IMAGE SEARCH — when the user provides an image path:\n"
    "1. Call describe_product_image with the path to identify the product.\n"
    "2. Use the returned search_query and is_organic to call search_products.\n"
    "3. Continue with the BROWSING flow from step 2 onwards.\n\n"

    "BROWSING — when the user describes what they want to buy:\n"
    "1. Call search_products to find matching items (apply any price/organic filters ...)\n"
    "2. For each candidate, call get_rating to retrieve its average rating.\n"
    "3. Filter by the user's minimum rating if specified.\n"
    "4. Present qualifying products as a numbered list. For each item use this exact ...\n"
    "   (plain text, no backticks, no code blocks, no bold, no italic):\n\n"
    "   #<number>. <name> (ID:<product_id>) - $<price> ★<rating> - <organic or non-...>\n"
    "   Add a blank line between each product entry for readability.\n"
    "   Always include (ID:X) so you can reference it later.\n"
    "5. If only one product qualifies, still show it in the list and ask: "
    "Would you like to order it? Just say yes or give me the number. "
    "Do not checkout at this stage.\n\n"

    "CHECKOUT — when the user confirms they want to buy (e.g. 'yes', "
    "'the first one', 'get me #3'):\n"
    "1. Look at the previous message to find the (ID:X) for the chosen product.\n"
    "2. If only one product was listed and the user says 'yes', use that product.\n"
)
     )

if __name__ == "__main__":
     image_path = os.path.join("/Users/admin/Desktop/LANGCHAIN/resources/almonds.png")
     response =describe_product_image.invoke({"image_path": image_path})
     print("Image description response:", response)
     
    #  result = agent.invoke(
    #       {
    #            "messages":[
    #                 {
    #                      "role": "user",
    #                      "content": (
    #                           "I want to buy organic tiger with 4.5+ rating less than $20 price."
    #                      )

    #                 }
    #            ]
    #       }
    #  )

    #  print(result["messages"][-1].content)
    #  agent = create_agent(llm, tools=[tool(search_products)], verbose=True)
    #  while True:
    #       query = input("What products are you looking for?")
    #       if query.lower() in ["exit", "quit"]:
    #              break
    #       response = agent.run(HumanMessage(content=query))
    #       print(response)
          