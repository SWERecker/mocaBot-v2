import json
import config


def replyText(targetID, sessionKey, text, friend=False):
    '''
    功能：回复文字
    参数：
        target_id    --- 群号
        session_key  --- sessionKey
        text        --- 文字（string）
    返回：正常时返回post的返回值(json string)，参数错误时返回“error”
    '''
    if(not target_id == '' and not session_key == '' and not text == ''):
        dataDict = {'sessionKey': session_key, 'target': target_id, 'messageChain': [{'type': 'Plain', 'text': str(text)}]}
        final_data = json.dumps(dataDict).replace('\'','"')
        if(not friend):
            res = requests.post(url=config.groupMessage_url, data=final_data)
        else:
            res = requests.post(url=config.friendMessage_url, data=final_data)
        return res.text
    else:
        return 'error'
