# Configure your host name
server_name = '127.0.0.1'
server_port = 5700
superman = 565379987
bot_id = 3270612406

# MiraiAPIHTTP
auth_data = {'authKey': 'd0bTYEOioR7TRs6E'}
verify_data = {'sessionKey': '', 'qq': bot_id}

auth_url = 'http://{}:{}/auth'.format(server_name, server_port)
verify_url = 'http://{}:{}/verify'.format(server_name, server_port)
random_url = 'http://api.mocabot.cn/api'
mute_url = 'http://{}:{}/mute'.format(server_name, server_port)
unmute_url = 'http://{}:{}/unmute'.format(server_name, server_port)

groupMessage_url = 'http://{}:{}/sendGroupMessage'.format(server_name, server_port)
friendMessage_url = 'http://{}:{}/sendFriendMessage'.format(server_name, server_port)
tempMessage_url = 'http://{}:{}/sendTempMessage'.format(server_name, server_port)

ws_addr = 'ws://{}:{}/message?sessionKey='.format(server_name, server_port)

# Mirai
mirai_path = 'C:\\mirai'


