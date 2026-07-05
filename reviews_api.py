"""
reads reviews from the reviews table in store.db and returns 
aggregated rating information for products.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

def get_product_reviews(product_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all reviews for the product
    cursor.execute("""
        SELECT AVG(rating) as average_rating, COUNT(*) as review_count 
        FROM reviews 
        WHERE product_id = ?
    """, (product_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "product_id": product_id,
            "average_rating": result[0],
            "review_count": result[1]
        }
    else:
        return {
            "product_id": product_id,
            "average_rating": None,
            "review_count": 0
        }
    
def get_ratings_for_products(product_ids: list) -> dict:
    """
    Returns average rating and review count for a list of product IDs.
    Each result includes: product_id, average_rating, review_count.
    """
    if not product_ids:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ','.join("?" * len(product_ids))
    cursor.execute(
        f"""
        SELECT product_id, AVG(rating) as average_rating, COUNT(*) as review_count 
        FROM reviews 
        WHERE product_id IN ({placeholders})
        GROUP BY product_id
    """, product_ids
    )
    rows = cursor.fetchall()
    conn.close()

    ratings_map = {row[0]: {"average_rating": row[1], "review_count": row[2]} for row in rows}
    return[
        {
            "product_id": product_id,
            "average_rating": ratings_map.get(product_id, {}).get("average_rating"),
            "review_count": ratings_map.get(product_id, {}).get("review_count", 0)
        }
        for product_id in product_ids
    ]


if __name__ == "__main__":
#single product reviews
    result = get_product_reviews(2)
    print("single product reviews:")
    print(f" Product {result['product_id']} - Average Rating: {result['average_rating']}, Review Count: {result['review_count']}")

#multiple product reviews
    print("\nmultiple product reviews:")
    results = get_ratings_for_products([1, 2, 3,7])
    for result in results:
        print(f" Product {result['product_id']} - Average Rating: {result['average_rating']}, Review Count: {result['review_count']}")