# import slack
import os
from flask import Flask, request
import requests
from threading import Thread
from slackeventsapi import SlackEventAdapter

app = Flask(__name__)

token = os.environ.get("SLACK_BOT_TOKEN")

slack_event_adapter = SlackEventAdapter(
    os.environ.get("SLACK_SIGNING_SECRET"),
    "/slack/events", app
)

prefixes = [
    {"/brainstorm": "brainstorm 10 points around the following idea"},
    {"/ideas": "provide business ideas for the following"},
    {"/joke": "write a joke on the following subject"},
    {"/expand": "expand on the following"},
]


def post_message(channel, message):
    import slack
    client = slack.WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    client.chat_postMessage(
        channel=channel,  # os.environ["SLACK_CHANNEL"],
        text=message,
    )
    return "success", 200


def get_prefix(key):
    for prefix in prefixes:
        if key in prefix:
            return prefix[key]

    return None


def create_openai_prompt(text, prefix):
    full_prompt = prefix+text
    print("Full prompt: " + full_prompt)
    response = requests.post(
        "https://api.openai.com/v1/engines/text-davinci-003/completions",
        json={"prompt": full_prompt, "max_tokens": 1000},
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY'] }"
        })
    message = response.json()["choices"][0]["text"]
    post_message("ideas", message)


@app.route("/")
def index():
    return {"message": "Hello, World!"}


@app.route("/slack/commands", methods=["POST"])
def home():
    command = request.form.get("command")
    message = request.form.get("text")
    prefix = get_prefix(command)
    print(f"message send: {message}")
    print(request.form.get("text"))
    if message is not None:
        # thr = Thread(
        #     target=create_openai_prompt,
        #     args=[message, prefix],
        #     daemon=False
        # )
        # thr.start()
        post_message("ideas", message)
        create_openai_prompt(message, prefix)
        response = {"message": "accepted"}, 200
        return response
    else:
        return {"message": "malformed request"}, 201


# @app.route("/slack/events", methods=["POST"])
@slack_event_adapter.on("app_mention")
def message(payload):
    event_data = payload.get("event", {})
    event_type = event_data.get("type")
    print(event_type)
    if event_type == "app_mention":
        channel_id = event_data.get("channel")
        user_id = event_data.get("user")
        text = event_data.get("text")
        post_message(channel_id, text)
    return {"message": "success", "challenge": event_data.get("challenge")}, 200


if __name__ == "__main__":
    app.run(debug=True)
