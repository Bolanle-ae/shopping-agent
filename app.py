import streamlit as st
import tempfile
import os
import json
from shopping_agent import agent, describe_product_image, search_products, checkout

st.set_page_config(page_title="Shopping Assistant", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .product-card {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .product-id {
        font-size: 0.75rem;
        color: #89b4fa;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .product-name { font-size: 1.05rem; font-weight: 700; margin: 0.2rem 0; }
    .product-price { color: #a6e3a1; font-weight: 600; }
    .product-desc { color: #9399b2; font-size: 0.88rem; margin-top: 0.3rem; }
    .organic-badge {
        display: inline-block;
        background: #40a02b22;
        color: #40a02b;
        border: 1px solid #40a02b55;
        border-radius: 20px;
        padding: 1px 8px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-left: 6px;
    }
    .upload-area {
        border: 2px dashed #313244;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        color: #6c7086;
    }
    div[data-testid="stFileUploader"] { margin-bottom: 0; }
</style>
""", unsafe_allow_html=True)

st.title("🛒 Shopping Assistant")
st.divider()

# --- Session state ---
for key, default in [("products", []), ("identified_as", ""), ("order_result", ""), ("chat_messages", [])]:
    if key not in st.session_state:
        st.session_state[key] = default

tab_image, tab_chat = st.tabs(["Image Search", "Chat"])

# ─────────────────────────────────────────────
# TAB 1 — Image Search
# ─────────────────────────────────────────────
with tab_image:
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        st.subheader("Upload a Product Image")
        uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")

        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)

            if st.button("Find Similar Products", type="primary", use_container_width=True):
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                with st.spinner("Analyzing image..."):
                    raw = describe_product_image.invoke({"image_path": tmp_path})
                os.unlink(tmp_path)

                try:
                    clean = raw.strip()
                    if clean.startswith("```"):
                        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                    data = json.loads(clean)
                except Exception:
                    data = {}

                with st.spinner("Searching database..."):
                    results_json = search_products.invoke({
                        "query": data.get("search_query", ""),
                        "is_organic": data.get("is_organic")
                    })
                    st.session_state.products = json.loads(results_json)
                    st.session_state.identified_as = data.get("product_type", "")
                    st.session_state.order_result = ""
                st.rerun()
        else:
            st.markdown('<div class="upload-area">Drag & drop or click to upload a product image</div>', unsafe_allow_html=True)

    with right:
        st.subheader("Matching Products")

        if st.session_state.products:
            if st.session_state.identified_as:
                st.caption(f"Identified as: **{st.session_state.identified_as}**")

            for p in st.session_state.products:
                organic_badge = '<span class="organic-badge">organic</span>' if p["is_organic"] else ""
                st.markdown(f"""
<div class="product-card">
    <div class="product-id">Order #{p['id']}</div>
    <div class="product-name">{p['name']}{organic_badge}</div>
    <div class="product-price">${p['price']:.2f}</div>
    <div class="product-desc">{p['description']}</div>
</div>
""", unsafe_allow_html=True)

            st.divider()
            st.markdown("**Enter an order number to place your order:**")
            col1, col2 = st.columns([2, 1])
            with col1:
                order_input = st.number_input("Order #", min_value=1, step=1, label_visibility="collapsed")
            with col2:
                if st.button("Place Order", type="primary", use_container_width=True):
                    result = checkout.invoke({"product_id": int(order_input)})
                    st.session_state.order_result = result
                    st.rerun()

            if st.session_state.order_result:
                st.success(st.session_state.order_result)

        else:
            st.markdown('<div class="upload-area" style="margin-top:1rem;">Products will appear here after you upload an image.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TAB 2 — Chat
# ─────────────────────────────────────────────
with tab_chat:
    st.subheader("Chat with your Shopping Assistant")
    st.caption("Search for products, ask about ratings, or place an order by typing below.")

    messages_container = st.container(height=520)
    with messages_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("e.g. Show me organic honey under $15"):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        with messages_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    result = agent.invoke({
                        "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
                    })
                    response = result["messages"][-1].content

                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
