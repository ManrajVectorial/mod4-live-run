"""Headers sent with every OpenRouter call (embeddings, chat and the health probe).

X-Title names the app in OpenRouter's usage records. It's an app label, not a model name,
URL or threshold, so it lives here rather than in .env.
"""

APP_TITLE = "Policy Assistant sample"
HEADERS = {"X-Title": APP_TITLE}
