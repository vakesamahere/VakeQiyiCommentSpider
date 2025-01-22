import requests,re,json,random,base64
import tool

class Spider:
    # User-agent pool
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; Pixel 3 XL Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/89.0"
    ]

    def get_random_user_agent(self):
        return random.choice(self.user_agents)

    def __init__(self):
        pass
    
    def get_comments(self,url):
        pass

class QiyiSpider(Spider):
    '''
    爱奇艺评论区爬虫
    特定后端服务端点，传入视频id输出评论，内容不在html中
    '''
    invalid_content_id="invalid_content_id"
    content_id_url = 'https://mesh.if.iqiyi.com/player/lw/lwplay/accelerator.js?apiVer=2'
    comment_url = 'https://sns-comment.iqiyi.com/v3/comment/get_baseline_comments.action'
    
    def __init__(self):
        super().__init__()
    
    def get_content_id(self,referer):
        headers = {
            "Referer": referer,
            "User-Agent": self.get_random_user_agent()
        }
        response = requests.get(self.content_id_url, headers=headers)
        if response.status_code == 200:
            match = re.search(r'"tvid":(\d+)', response.text)
            if match:
                tvid = match.group(1)
                print("get content_id:", tvid)
                return tvid
            else:
                print("content_id matching failed")
                return self.invalid_content_id
        else:
            print("content_id connecting failed: ", response.status_code)
            return self.invalid_content_id

    def get_comments(self, url):
        '''
        直接调用
        '''
        tvid = self.get_content_id(url)
        if tvid==self.invalid_content_id:
            return []
        params = {
            "page_size":40,
            "sort":"HOT",
            "business_type":17,
            "agent_type":30,
            "content_id":eval(tvid)
        }
        try:
            headers = {
                "User-Agent": self.get_random_user_agent()
            }
            response = requests.get(self.comment_url, params=params,headers=headers)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            comments = json.loads(response.text)
            comments_list = []
            for item in comments.get('data').get('comments'):
                comments_list.append(item.get('content'))
            return comments_list
        except requests.RequestException as e:
            print(f"Error loading URL: {e}")
            return []
        except:
            print(f"Data Structure Error")
            return []

class TencentSpider(Spider):
    '''
    腾讯视频评论区爬虫
    调用后端服务，发送post请求直接拿到评论
    '''

    comment_url = "https://pbaccess.video.qq.com/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData?vversion_name=1.0.0&vplatform=2&guid=53034ef6b7b39fff&video_omgid=53034ef6b7b39fff"
    payload_template = {
        "page_params": {
            "data_key": "",
            "page_id": "ip_doki_rec",
            "page_type": "channel_operation"
        },
        "page_context":{
            "page_index":"1",
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://v.qq.com/",
    }


    def __init__(self):
        super().__init__()

    def get_comments(self,url,pages=10):
        payload = self.payload_template.copy()
        data_key=self._get_data_key(url)
        payload['page_params']['data_key'] = data_key

        comments_list = []
        # first page
        page = 1
        while True:
            headers = self.headers.copy()
            headers['User-Agent'] = self.get_random_user_agent()
            response = requests.post(self.comment_url, json=payload, headers=headers)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            if response.status_code!=200:
                break
            
            comments = self._decode_comments(response.json())
            comments_list+=comments

            new_page_context = self._decode_page_context(response.json())
            if new_page_context is None:
                break
            payload['page_context'] = new_page_context
            
            if page>pages:
                break
            page+=1
        return comments_list
    
    def _get_data_key(self,url):
        response = requests.post(url,headers={
            "User-Agent": self.get_random_user_agent()
            })
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        if response.status_code!=200:
            return None
        html_content = response.text
        pattern = r'content="http://v\.qq\.com/x/cover/([^/]+)/([^/]+)\.html"'
        match = re.search(pattern, html_content)
        if match:
            cid = match.group(1)
            vid = match.group(2)
            result_string = f"cid={cid}&vid={vid}"
            return result_string
        else:
            print("fail matching data_key")
            return None

    def _decode_comments(self,data):
        comments = []
        try:
            items = data['data']['module_list_datas']
            for item in items:
                # 解析到json字符串
                complex_json_text = item['module_datas'][0]['item_data_lists']['item_datas'][0]['complex_json']
                # 加载为dict
                complex_json = json.loads(complex_json_text)
                # 解析到base64编码的字符串
                content_b64=complex_json['content']['content']
                # 解码
                content_bytes=base64.urlsafe_b64decode(content_b64)
                content = content_bytes.decode('utf-8')
                comments.append(content)
        except:
            pass
        return comments
    
    def _decode_page_context(self,data):
        try:
            return data['data']['next_page_context']
        except:
            return None
        

if __name__ == '__main__':
    spider = TencentSpider()
    comments = spider.get_comments('https://v.qq.com/x/cover/mzc00200cqecotm/g0042gw1ak3.html',5)
    print('腾讯视频\n',comments)
    spider = QiyiSpider()
    comments = spider.get_comments('https://www.iqiyi.com/v_19rrjvkzb4.html?vfrmrst=0&vfrm=3&vfrmblk=pca_115_word_enlarge')
    print('爱奇艺\n',comments)