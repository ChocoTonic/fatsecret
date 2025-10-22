from flask import Flask, redirect, request, url_for

from fatsecret import Fatsecret

# Be sure to add your own keys
consumer_key = None
consumer_secret = None


app = Flask(__name__)
fs = Fatsecret(consumer_key, consumer_secret)


@app.route("/")
def index():
    if request.args.get("oauth_verifier"):

        session_token = fs.authenticate(request.args.get("oauth_verifier"))

        return redirect(url_for("profile"))

    else:
        return "<ul><li><a href={0}>Authenticate Access Here</a></li>\
            <li><a href={1}>Example Search: Chicken Soup</a></li>\
            <li><a href={2}>Example Item Lookup: Item #1750</a></li>".format(
            url_for("authenticate"), "search/chicken%20soup", "food/1750"
        )


@app.route("/auth")
def authenticate():
    return redirect(fs.get_authorize_url(callback_url="http://127.0.0.1:5000"))


@app.route("/search/<search_term>")
def search(search_term):
    search_results = fs.foods_search(search_term, page_number=1, max_results=10)

    return "<h1>Search Results: {0}</h1><div>{1}</div>".format(
        search_term, search_results
    )


@app.route("/food/<item>")
def food(item):
    food_item = fs.food_get(item)

    return "<h1>Food Item</h1><div>{}</div>".format(food_item)


@app.route("/profile")
def profile():
    food = fs.foods_get_most_eaten()

    return "<h1>Profile</h1><div><strong>Most Eaten Foods</strong><br>{}</div>".format(
        food
    )


if __name__ == "__main__":
    app.run()
