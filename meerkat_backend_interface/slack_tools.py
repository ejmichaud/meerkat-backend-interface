import os
import slacker


def notify_slack(message, channel='#active_observations'):
    """Publishes message to slack channel

    Args:
        message (str): the message to send
        channel (str): the chat to send to (starts with # if a channel)
            --> defaults to '#active_observations'
    Returns:
        None

    Examples:
        >>> notify_slack('SKA is on fire!!!')
        >>> notify_slack('Found aliens!', '#listen')
    """
    token = os.environ['SLACK_TOKEN']
    slack = slacker.Slacker(token)
    slack.chat.post_message(channel, message)
