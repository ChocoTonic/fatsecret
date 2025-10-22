import os
from pprint import pprint

from dotenv import load_dotenv

from fatsecret import Fatsecret
from fatsecret.auth import fatsecret_authenticate

load_dotenv()

consumer_key = os.getenv("FATSECRET_CONSUMER_KEY")
consumer_secret = os.getenv("FATSECRET_CONSUMER_SECRET")
username = os.getenv("FATSECRET_USERNAME")
password = os.getenv("FATSECRET_PASSWORD")

print("Using the following credentials:")
print(f"  Consumer Key: {consumer_key if consumer_key else '[NOT SET]'}")
print(f"  Consumer Secret: {consumer_secret if consumer_secret else '[NOT SET]'}")


if not consumer_key or not consumer_secret:
    raise ValueError(
        "Missing API credentials. Please set FATSECRET_CONSUMER_KEY and "
        "FATSECRET_CONSUMER_SECRET environment variables."
    )

# Create unauthenticated client for public API calls
fs = Fatsecret(consumer_key, consumer_secret)

# Test Calls w/o authentication

print("\n\n ---- No Authentication Required ---- \n\n")

foods = fs.foods_search("Tacos")
print(f"Food Search Results: {len(foods)}")
pprint(foods)
print()

food = fs.food_get("1345")
print("Food Item 1345")
pprint(food)
print()

recipes = fs.recipes_search("Tomato Soup")
print("Recipe Search Results:")
pprint(recipes)
print()

recipe = fs.recipe_get("88339")
print("Recipe 88339")
pprint(recipe)
print()

# Test Calls with 3 Legged Oauth (Automated Authentication)

print("\n\n ------ OAuth Example (Automated) ------ \n\n")

# Automatically authenticate using username/password or saved tokens
# This function will:
# 1. Check for FATSECRET_ACCESS_TOKEN and FATSECRET_ACCESS_SECRET env vars first
# 2. If not found, use FATSECRET_USERNAME and FATSECRET_PASSWORD to automate login
# 3. Return an authenticated Fatsecret instance or None
fs_authenticated = fatsecret_authenticate(
    username=username,
    password=password,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
)

if not fs_authenticated:
    print("Authentication failed or credentials not provided.")
    print("Set FATSECRET_USERNAME and FATSECRET_PASSWORD environment variables,")
    print(
        "or set FATSECRET_ACCESS_TOKEN and FATSECRET_ACCESS_SECRET to use saved tokens."
    )


print("Successfully authenticated!")

# Get the session token for future reuse
session_token = (
    fs_authenticated.access_token,
    fs_authenticated.access_token_secret,
)
print(f"Session Token: {session_token}")
print(
    "Save these tokens as FATSECRET_ACCESS_TOKEN and FATSECRET_ACCESS_SECRET for future use!\n"
)

# Now make authenticated API calls

recipes = fs_authenticated.recipes_search("Enchiladas")
print(f"Recipe Search Results: {len(recipes)}")
pprint(recipes)
print()

profile = fs_authenticated.profile_get()
print("Profile:")
pprint(profile)
