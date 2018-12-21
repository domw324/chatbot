from flask import Flask, request
import os
from pprint import pprint as pp
import requests
import random
import json
from datetime import datetime
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

api_url = 'https://api.hphk.io/telegram' # 우회 주소
token = os.getenv('TELE_TOKEN')

@app.route(f'/{token}', methods=['POST'])
def telegram():
    # - - - - NAVERapi를 사용하기 위한 변수 - - - - 
    naver_client_id = os.getenv('NAVER_ID')
    naver_client_secret = os.getenv('NAVER_SECRET')
    # - - - - - - - - - - - - - - - - - - - - - - - 
    
    tele_dict = request.get_json()
    # pp(request.get_json()) # pp는 우리가 보기 편한 형태로 나타내 줌
    
    chat_id = tele_dict["message"]["from"]["id"] # user id
    text = tele_dict.get("message").get("text") # text contents
    # text = tele_dict["message"]["text"] # 이렇게 쓰면 이미지를 넣을 때 오류가 날 수 있다.
    
    # 사용자가 이미지를 넣었는지 체크
    img = False
    trans = False
    if tele_dict.get("message").get("photo") is not None:
        img = True
    else:
        # text 제일 앞 두글자가 '변역'?
        if text[:2] == "번역":
            trans = True
            text = text.replace("번역", "")
    
    if trans:
        # 아래 get()안의 내용은 NAVER developer의 파파고 NMT API 가이드에 있음
        papago = requests.post("https://openapi.naver.com/v1/papago/n2mt",
            headers = {
                "X-Naver-Client-Id" : naver_client_id,
                "X-Naver-Client-Secret" : naver_client_secret
            },
            data = {
                "source" : "ko",
                "target" : "en",
                "text" : text
            }
        )
        trans_dict = papago.json() # 결과를 dict 형식으로 변환
        text = trans_dict["message"]["result"]["translatedText"] # text 설정
        
    elif img:
        text = "사용자가 이미지를 넣었어요"
        # 텔레그램에게서 사진 정보 가져오기
        file_id = tele_dict["message"]["photo"][-1]["file_id"]
        file_path = requests.get(f"{api_url}/bot{token}/getFile?file_id={file_id}").json()["result"]["file_path"]
        file_url = f"{api_url}/file/bot{token}/{file_path}"
        
        # 사진을 네이버 유명인인식api로 넘겨주기
        file = requests.get(file_url, stream=True)
        clova = requests.post("https://openapi.naver.com/v1/vision/celebrity",
            headers = {
                "X-Naver-Client-Id" : naver_client_id,
                "X-Naver-Client-Secret" : naver_client_secret
            },
            files = {
                "image" : file.raw.read()
            }
        )
        # 가져온 데이터 중에서 필요한 정보 빼오기
        if clova.json().get("info").get("faceCount"):
            text = clova.json()["faces"][0]["celebrity"]["value"]
        else:
            text = "누군지 모르겠소. 4달러."
        
    elif "메뉴" in text:
        menu_list = ["한식", "중식", "양식", "분식", "선택식", "take out"]
        text = random.choice(menu_list)
    
    elif "로또" in text:
        if "자동" in text:
            text = random.sample(list(range(1,46)), 6)
            text.sort()
        elif "당첨" in text:
            lotto_url = 'https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo=837'
            lotto_res = requests.get(lotto_url).text # 여기에서 json형식으로 받는다. type(res) = str
            lotto_dict = json.loads(lotto_res) #json 내부 함수 활용 json->dict 변환
            date = lotto_dict["drwNoDate"] # 추첨일
            turn = lotto_dict["drwNo"] # 추첨회차
            week = [] # 추첨번호
            for i in range(1,7):
                temp_str = "drwtNo{0}".format(i)
                week.append(lotto_dict[temp_str])
            bonus = lotto_dict["bnusNo"] # 보너스번호
            text = f"추첨일자 : {date}\n회차 : {turn}\n\n당첨 번호 : {week}\n보너스 번호 : {bonus}\n"
    
    elif "실시간 검색어" in text:
        silgum_url = "https://www.daum.net"
        silgum_res = requests.get(silgum_url).text
        
        soup = BeautifulSoup(silgum_res, 'html.parser')
        pick = soup.select('#mArticle > div.cmain_tmp > div.section_media > div.hotissue_builtin.hide > div.realtime_part > ol > li > div > div:nth-of-type(1) > span.txt_issue > a')
        
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second
        
        text = f"현재 시각 : {hour}시 {minute}분 {second}초\n다음 실시간 검색어는\n"
        i = 1
        for p in pick:
            text += (f"\n{i}. " + p.text)
            i = i + 1
    
    else:
        text = "그런건 모르겠소. 4달러."
        
    requests.get(f'{api_url}/bot{token}/sendMessage?chat_id={chat_id}&text={text}')
    return '', 200

app.run(host=os.getenv('IP', '0.0.0.0'), port=int(os.getenv('PORT',8080)))