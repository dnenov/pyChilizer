#! python3
import slack

# from pyrevit import HOST_APP, EXEC_PARAMS
# from pyrevit import revit, script
# import hooks_logger as hl


# args = EXEC_PARAMS.event_args
#
# hl.log_hook(__file__,
#     {
#         "cancellable?": str(args.Cancellable),
#         "doc": str(revit.doc),
#         "doc_location": str(args.Location),
#         "options": str(args.Options),
#     },
#     log_doc_access=True
# )

slack_token = 'xoxb-315302503440-2634639326087-Xtjm0FNGFe9K0eAI9ltKTMj4'
client = slack.WebClient(token=slack_token)

def post_message(message_text):
    client.chat_postMessage(channel='#synch_bot', text=message_text)

post_message("I am here to take over the world")
