#! python3
import slack

slack_token = 'xoxb-315302503440-2634639326087-Xtjm0FNGFe9K0eAI9ltKTMj4'
client = slack.WebClient(token=slack_token)

def post_message(message_text):
    client.chat_postMessage(channel='#synch_bot', text=message_text)