#Configure your host name
server_name = '192.168.1.225'
server_port = 5700

# MiraiAPIHTTP
auth_data = {'authKey':'d0bTYEOioR7TRs6E'}
verify_data = {'sessionKey': '','qq': 3270612406 }

auth_url = 'http://{}:{}/auth'.format(server_name,server_port)
verify_url = 'http://{}:{}/verify'.format(server_name,server_port)

groupMessage_url = 'http://{}:{}/sendGroupMessage'.format(server_name,server_port)
friendMessage_url = 'http://{}:{}/sendFriendMessage'.format(server_name,server_port)
tempMessage_url = 'http://{}:{}/sendTempMessage'.format(server_name,server_port)