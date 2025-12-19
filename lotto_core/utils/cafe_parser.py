from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import configparser
import os


class CafeParser:
    LOGIN_URL = 'https://nid.naver.com/nidlogin.login'
    BOARD_URL = 'https://cafe.naver.com/f-e/cafes/29572332/menus/22'

    def __init__(self):
        self.round_no = 0
        self.round_info = None

        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'access.ini')
        config.read(config_path)
        self.NAVER_ID = config['NAVER']['ID']
        self.NAVER_PW = config['NAVER']['PW']

        # 크롬 옵션 설정 (서버용)
        options = Options()
        options.add_argument("--headless")  # GUI 없는 서버이므로 필수
        #options.add_argument("--no-sandbox")
        #options.add_argument("--disable-dev-shm-usage")
        #options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

        # 드라이버 자동 설치 및 실행
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        #self.driver = webdriver.Chrome()

    def login(self):
        self.driver.get(self.LOGIN_URL)
        time.sleep(2)

        # 일반적인 send_keys는 캡차를 유발하므로 JS 주입 방식 사용 (자동 입력 방지 우회)
        self.driver.execute_script(f"document.getElementById('id').value = '{self.NAVER_ID}'")
        self.driver.execute_script(f"document.getElementById('pw').value = '{self.NAVER_PW}'")
        time.sleep(2)
        self.driver.find_element(By.ID, 'log.login').click()

        # 로그인이 완료될 때까지 대기
        WebDriverWait(self.driver, 10).until(
            EC.url_changes(self.LOGIN_URL)
        )
        time.sleep(2)

    def parse_latest_round(self):
        self.driver.get(self.BOARD_URL)
        time.sleep(2)
        wait = WebDriverWait(self.driver, 10)

        # 게시판에서 최신글 찾아 진입
        selector = "tbody tr:not(.board-notice) td div.inner_list a.article"
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        element.click()
        time.sleep(2)

        # 게시판 최신글 분석
        self.driver.switch_to.frame("cafe_main")
        time.sleep(2)

        selector = '.title_area .title_text'
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        title = element.text.strip()

        selector = '.se-main-container, .content-container, .article_viewer'
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        body = element.text.strip()

        self._parse_content(title, body)

    def _parse_content(self, title, body):
        start_index = title.find('제') + 1
        end_index = title.find('회')
        no = title[start_index:end_index]

        start_index = title.find('(') + 1
        end_index = title.find(')')
        date = title[start_index:end_index]
        splits = date.split('.')
        if (len(splits[1]) == 1): splits[1] = '0' + splits[1]
        if (len(splits[2]) == 1): splits[2] = '0' + splits[2]
        date = f'{splits[0]}.{splits[1]}.{splits[2]}'

        lines = body.split('\n')

        ballset_found = False
        d1_found = False
        d2_found = False
        d3_found = False
        machine = ''
        ballset = ''
        garo = ''
        d1 = []
        d2 = []
        d3 = []
        for line in lines:

            if (ballset != ''): ballset_found = False
            if (len(d1) >= 7): d1_found = False
            if (len(d2) >= 7): d2_found = False
            if (len(d3) >= 7): d3_found = False

            if ('1' in line and '볼세트' in line):
                if (line.strip().endswith('볼세트') == False):
                    splits = line.strip().split(' ')
                    ballset = splits[-1]
                else:
                    ballset_found = True
            elif ('2' in line and '모의' in line): d1_found = True
            elif ('3' in line and '당첨번호' in line): d2_found = True
            elif ('4' in line and '당첨번호' in line): d3_found = True
            elif (machine == '' and '*' in line and '추첨기' in line and '호기' in line):
                splits = line.strip().split(':')
                machine = splits[1].replace('호기', '').strip()
            elif (garo == '' and line.strip().startswith('*볼배열방식')):
                try:
                    splits = line.strip().split(':')
                    garo = splits[1].replace('배열', '').strip()
                except:
                    splits = line.strip().split(' ')
                    garo = splits[1].replace('배열', '').strip()
            elif (ballset_found == True): ballset = line.strip()
            elif (len(d1) < 7 and d1_found == True):
                #d1.append(line.strip())
                splits = line.strip().split(' ')
                for splititem in splits:
                    if (len(splititem.strip()) != 0): d1.append(splititem.strip())
            elif (len(d2) < 7 and d2_found == True):
                #d2.append(line.strip())
                splits = line.strip().split(' ')
                for splititem in splits:
                    if (len(splititem.strip()) != 0): d2.append(splititem.strip())
            elif (len(d3) < 7 and d3_found == True):
                #d3.append(line.strip())
                splits = line.strip().split(' ')
                for splititem in splits:
                    if (len(splititem.strip()) != 0): d3.append(splititem.strip())

        if (garo == '가로로'): garo = '가로'
        if (garo == '세로로'): garo = '세로'

        if (no == '' or date == ''):
            raise Exception('## no/date error !!!!')
        if (machine != '1' and machine != '2' and machine != '3'):
            raise Exception('## machine error !!!!')
        if (ballset != '1' and ballset != '2' and ballset != '3' and ballset != '4' and ballset != '5'):
            raise Exception('## ballset error !!!!')
        if (garo != '가로' and garo != '세로'):
            raise Exception('## garo error !!!!')
        if (len(d1) != 7 or d1[0].isdigit() != True or d1[1].isdigit() != True or d1[2].isdigit() != True or
            d1[3].isdigit() != True or d1[4].isdigit() != True or d1[5].isdigit() != True or d1[6].isdigit() != True):
            raise Exception('## d1 error !!!!')
        if (len(d2) != 7 or d2[0].isdigit() != True or d2[1].isdigit() != True or d2[2].isdigit() != True or
            d2[3].isdigit() != True or d2[4].isdigit() != True or d2[5].isdigit() != True or d2[6].isdigit() != True):
            raise Exception('## d2 error !!!!')
        if (len(d3) != 7 or d3[0].isdigit() != True or d3[1].isdigit() != True or d3[2].isdigit() != True or
            d3[3].isdigit() != True or d3[4].isdigit() != True or d3[5].isdigit() != True or d3[6].isdigit() != True):
            raise Exception('## d3 error !!!!')

        self.round_no = no
        self.round_info = {
            'rid': no, # 회차
            'date': date, # 추첨일
            'rule_ballset': ballset, # 추첨방식: 볼세트 (1~3)
            'rule_garo': garo, # 추첨방식: 모름/가로/세로 (0~2)
            'rule_machine': machine, # 추첨방식: 추첨기 (1~3)
            'practice1': d1[0], # 모의추첨번호: 1
            'practice2': d1[1], # 모의추첨번호: 2
            'practice3': d1[2], # 모의추첨번호: 3
            'practice4': d1[3], # 모의추첨번호: 4
            'practice5': d1[4], # 모의추첨번호: 5
            'practice6': d1[5], # 모의추첨번호: 6
            'practice7': d1[6], # 모의추첨번호: 7
            'drawing1': d2[0], # 당첨번호(추첨순): 1
            'drawing2': d2[1], # 당첨번호(추첨순): 2
            'drawing3': d2[2], # 당첨번호(추첨순): 3
            'drawing4': d2[3], # 당첨번호(추첨순): 4
            'drawing5': d2[4], # 당첨번호(추첨순): 5
            'drawing6': d2[5], # 당첨번호(추첨순): 6
            'drawing7': d2[6], # 당첨번호(추첨순): 7
            'number1': d3[0], # 당첨번호(오름차순): 1
            'number2': d3[1], # 당첨번호(오름차순): 2
            'number3': d3[2], # 당첨번호(오름차순): 3
            'number4': d3[3], # 당첨번호(오름차순): 4
            'number5': d3[4], # 당첨번호(오름차순): 5
            'number6': d3[5], # 당첨번호(오름차순): 6
            'number7': d3[6], # 당첨번호(오름차순): 7
        }


if __name__ == "__main__":
    parser = CafeParser()
    parser.login()
    parser.parse_latest_round()
    print(parser.round_info)
