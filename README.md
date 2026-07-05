# Shopping Assistant

A Streamlit app that helps you search and order products from a local SQLite store, either by uploading a product photo or by chatting with an AI shopping agent (built with LangChain + Anthropic Claude).

## Features

- **Image search** — upload a product photo, the vision model identifies it and finds matching products.
- **Chat** — ask for products in natural language (e.g. "organic honey under $15"), get ratings, and place an order.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Anthropic API key:

```bash
cp .env.example .env
```

## Run

```bash
streamlit run app.py
```

## Project structure

- `app.py` — Streamlit UI
- `shopping_agent.py` — LangChain agent, tools (search, checkout, image description)
- `reviews_api.py` — product ratings/reviews lookup
- `store.db` — SQLite database (products, orders, reviews)
- `resources/` — sample product images for testing
