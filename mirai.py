import json
import config
import requests
import logging
import os
import time


def mirai_auth():
    """
    功能：mirai认证
    参数：无
    返回：sessionKey，错误时返回错误码
    """
    auth_json = {}

    r_auth_json = requests.post(config.auth_url, json.dumps(config.auth_data))
    # logging.info(r_auth_json.text)
    r_auth_json = json.loads(r_auth_json.text)
    config.verify_data['sessionKey'] = r_auth_json.get('session')

    r_verify_json = requests.post(config.verify_url, json.dumps(config.verify_data))
    r_verify_json = json.loads(r_verify_json.text)
    # logging.info('收到：' + str(r_verify_json))

    if r_verify_json.get('code') == 0:
        logging.info('收到sessionKey:{}, 储存到临时文件, 设置超时时间:25分钟, 将新json写入本地文件'.format(r_auth_json.get('session')))
        auth_json['auth_key'] = r_auth_json['session']
        time_expire = int(time.time()) + (25 * 60)
        auth_json['expire_time'] = time_expire
        with open(os.path.dirname(os.path.abspath(__file__)) + '/auth.json', 'w', encoding='utf-8') as auth_file:
            auth_file.write(json.dumps(auth_json))
        return r_auth_json['session']
    else:
        logging.error('返回错误，错误代码：{}'.format(r_verify_json.get('code')))
        return r_verify_json.get('code')


def check_if_key_expire(cache_time):
    """
    功能：检查时间戳是否超时
    参数：{
        cache_time : 缓存的时间戳
    }
    返回：超时：True，未超时：False
    """
    time_now = int(time.time())
    if time_now > cache_time:
        return True
    else:
        return False


def mirai_init_auth_key():
    """
    功能：初始化mirai认证
    参数：无
    返回：sessionKey，错误时返回错误码
    """
    try:
        with open(os.path.dirname(os.path.abspath(__file__)) + '/auth.json', 'r', encoding='utf-8') as auth_file:
            auth_json = json.loads(auth_file.read())
            local_expire_time = auth_json.get('expire_time')
            local_auth_key = auth_json.get('auth_key')
    except IOError:
        logging.warning("IOError:打开本地auth.json失败")
        local_auth_key = ''
        local_expire_time = 0

    if local_auth_key == '' or check_if_key_expire(local_expire_time):
        logging.info("无本地缓存sessionKey或者sessionKey已超时,更新sessionKey")
        return mirai_auth()
    else:
        logging.info("本地缓存命中")
        return local_auth_key


def mirai_reply_text(target_id, session_key, text, friend=False):
    """
    功能：回复文字
    参数：{
        target_id    :  群号/QQ号,
        session_key  :  sessionKey,
        text         :  文字（string）
    }
    返回：，参数错误时返回"error_invalid_parameter"
    """
    if not target_id == '' and not session_key == '' and not text == '':
        data_dict = {'sessionKey': session_key, 'target': target_id,
                     'messageChain': [{'type': 'Plain', 'text': str(text)}]}
        final_data = json.dumps(data_dict).replace('\'', '"').strip('"')
        if not friend:
            message_type = 'GROUP'
            res = requests.post(url=config.groupMessage_url, data=final_data)
        else:
            message_type = 'FRIEND'
            res = requests.post(url=config.friendMessage_url, data=final_data)
        logging.info("[EVENT] reply_text => {m_type}, {target} : {content}".format(target=target_id, content=text,
                                                                                   m_type=message_type))
        r_json = json.loads(res.text)
        return r_json.get('code'), r_json.get('messageId')
    else:
        return 'error_invalid_parameter'


def mirai_reply_image(target_id, session_key, path='', image_id='', friend=False):
    """
    功能：回复图片
    参数：{
        target_id    :  群号/QQ号，
        session_key  :  sessionKey,
        path         :  图片相对于 %MiraiPath%/plugins/MiraiAPIHTTP/images/
        [图片id]     :  图片ID(可选)
    }
    返回：正常时返回post的返回值(json string)，参数错误时返回"error_invalid_parameter"
    """
    if not target_id == '' and not session_key == '':
        data_dict = {"sessionKey": session_key, "target": target_id, "messageChain": [{"type": "Image"}]}

        if path == '':
            data_dict['messageChain'][0]['imageId'] = image_id
        elif image_id == '':
            data_dict['messageChain'][0]['path'] = path

        final_data = json.dumps(data_dict).replace('\'', '"').strip('"')
        if not friend:
            message_type = 'GROUP'
            res = requests.post(url=config.groupMessage_url, data=final_data)
        else:
            message_type = 'FRIEND'
            res = requests.post(url=config.friendMessage_url, data=final_data)
        logging.info(
            "[EVENT] reply_image => {m_type}, {target} : path={p_path}, imageId={p_id}".format(target=target_id,
                                                                                               p_path=path,
                                                                                               p_id=image_id,
                                                                                               m_type=message_type))
        r_json = json.loads(res.text)
        return r_json.get('code'), r_json.get('messageId')
    else:
        return 'error_invalid_parameter'


def mirai_reply_message_chain(target_id, session_key, message, friend=False):
    """
    功能：回复messageChain
    参数：{
        target_id    :  群号/QQ号,
        session_key  :  sessionKey,
        message      :  messageChain 是一个列表(List)，包含要发送的messageChain,
        friend       :  True/False [是否为好友消息]
    }
    返回：正常时返回post的返回值(json string)，参数错误时返回"error_invalid_parameter"
    """
    if not target_id == '' and not session_key == '':
        data_dict = {"sessionKey": session_key, "target": target_id, "messageChain": message}

        final_data = json.dumps(data_dict).replace('\'', '"').strip('"')
        if not friend:
            res = requests.post(url=config.groupMessage_url, data=final_data)
            message_type = 'GROUP'
        else:
            res = requests.post(url=config.friendMessage_url, data=final_data)
            message_type = 'FRIEND'
        r_json = json.loads(res.text)
        logging.info("[EVENT] reply_message_chain => {m_type}, {target} : messageChain:{msg}".format(target=target_id,
                                                                                                     m_type=message_type,
                                                                                                     msg=message))
        return r_json.get('code'), r_json.get('messageId')
    else:
        return 'error_invalid_parameter'


def mirai_fetch_group_id(data):
    """
    功能：取群号
    参数：{
        data  :  收到的json
    }
    返回：群号，获取错误时返回0
    """
    try:
        return data["sender"]["group"]["id"]
    except Exception as e:
        return 0


def mirai_fetch_user_id(data):
    """
    功能：取用户QQ号
    参数：{
        data  :  收到的json
    }
    返回：QQ号，获取错误时返回0
    """
    try:
        return data["sender"]["id"]
    except Exception as e:
        return 0


def mirai_fetch_sender_permission(data):
    """
    功能：取用户在群组中的权限（分为普通用户MEMBER，管理员ADMINISTRATOR，群主OWNER）
    参数：{
        data  :  收到的json
    }
    返回：权限(str)，获取错误时返回"error_undefined"
    """
    try:
        return data["sender"]["permission"]
    except Exception as e:
        return 'error_undefined'


def mirai_fetch_message_chain(data):
    """
    功能：取收到消息完整的messageChain(list)
    参数：{
        data  :  收到的json
    }
    返回：messageChain(list)，获取错误时返回"error_undefined"
    """
    try:
        return data["messageChain"]
    except Exception as e:
        return 'error_undefined'


def mirai_fetch_message_type(data):
    """
    功能：取收到消息的类型
    参数：{
        data  :  收到的json
    }
    返回：收到消息的类型，获取错误时返回"error_undefined"
    """
    try:
        return data["type"]
    except Exception as e:
        return 'error_undefined'


def mirai_fetch_text(data):
    """
    功能：取文字消息
    参数：{
        data  :  收到的json
    }
    返回：收到的消息的文本，去除空格
    """
    texts = ""
    for n in range(len(data["messageChain"])):
        if data["messageChain"][n]["type"] == "Plain":
            texts += data["messageChain"][n]["text"]
            texts = texts.replace(" ", "")
    return texts


def mirai_fetch_image_id(data):
    """
    功能：取收到图片的ID
    参数：{
        data  :  收到的json
    }
    返回：图片ID列表(List)
    """
    image_ids = []
    for n in range(len(data["messageChain"])):
        if data["messageChain"][n]["type"] == "Image":
            image_ids.append(data["messageChain"][n]["imageId"])
    return image_ids


def mirai_fetch_image_url(data):
    """
    功能：取收到图片的URL
    参数：{
        data  :  收到的json
    }
    返回：图片URL列表(List)
    """
    image_urls = []
    for n in range(len(data["messageChain"])):
        if data["messageChain"][n]["type"] == "Image":
            image_urls.append(data["messageChain"][n]["url"])
    return image_urls
