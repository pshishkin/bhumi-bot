import datetime
import json
import time
import settings
from telethon import TelegramClient, sync


if __name__ == '__main__':
    # Use your own values here
    api_id = settings.TG_API_ID
    api_hash = settings.TG_API_HASH

    client = TelegramClient('Session_details', api_id, api_hash)
    phone_number = settings.TG_PHONE_NUMBER

    client.connect()
    print("Connected")
    if not client.is_user_authorized():
        client.send_code_request(phone_number)
        me = client.sign_in(phone_number, input('Enter code: '))

    # get all the users and print them
    # for u in client.iter_participants(channel, search='ba', aggressive=True):
    #     print(u.id, u.username, u.first_name)

    dialogs = list(client.iter_dialogs(limit=20))
    for i, c in enumerate(dialogs):
        print(i, c.entity.id, c.name)

    dialog = dialogs[int(input('Enter dialog number to parse: '))]
    print(dialog)

    # for u in client.iter_participants(channel, aggressive=True):
    #     print(u.id, u.username, u.first_name)

    sender_ids = {}
    mid = None

    user_dict = {}
    def process_message(m):
        if m.sender_id not in user_dict:
            user_dict[m.sender_id] = {
                'messages_sent': 0,
                'last_message_timestamp': m.date.strftime("%Y-%m-%d"),
            }
            # print(m)
        user_dict[m.sender_id]['messages_sent'] += 1


    for m in client.iter_messages(dialog.entity.id, limit=1):
        mid = m.id
        date = m.date
        process_message(m)

    COLLECT_OVER_DAYS = 365*2
    # COLLECT_OVER_DAYS = 10
    for _ in range(300):
        time.sleep(1)
        local_users = 0
        for m in client.iter_messages(dialog.entity.id, limit=100, offset_id=mid):
            local_users += 1
            mid = m.id
            if date == m.date:
                break
            date = min(date, m.date)
            if datetime.datetime.now(tz=datetime.timezone.utc) - date > datetime.timedelta(days=COLLECT_OVER_DAYS):
                break
            process_message(m)
            # print(m.id, m.sender_id, m.date)
        print(f'found {len(user_dict)} users over period till {date}, {local_users}')
        if datetime.datetime.now(tz=datetime.timezone.utc) - date > datetime.timedelta(days=COLLECT_OVER_DAYS):
            break
        if local_users < 3:
            break

    print(f"found {len(user_dict)} users")

    # save this json to file with name of the channel
    with open(f"{settings.SNAPSHOTS_DIR}{input('Enter json file name: ')}.json", 'w') as f:
        f.write(json.dumps({'name': input('Назови группу: '), 'users': user_dict}))

    # for m in client.iter_messages(channel, limit=100, offset_id=mid):
    #     mid = m.id
    #     sender_ids[m.sender_id] = m.date
    #
    # print(len(sender_ids))

    # participants = client.get_participants(channel, aggressive=True)
    # print(len(participants))
    # print(participants)
    # print()
    #
    # participants = client.get_participants(channel, search='ba', aggressive=True)
    # print(len(participants))
    # print(participants)

    client.disconnect()
    print("Disconnected")
