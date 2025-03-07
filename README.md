# Twitch2Youtube
This program can download twitch hightlight and upload to youtube one by one automatically.
## Installation
download exe file from google drive
<https://drive.google.com/file/d/1hTnu_yNNi3DkbRzG7L-qbI41xY9kBpjK/view?usp=drive_link>
## Usage
---
1. Enter your twitch name 
2. Login Youtube account, it will create ***token.pickle*** file to record your login infornation. ***If you want to change an account, just delete it and login again.***    
3. You can choose upload your video in ***private*** or ***public***.    
4. You can choose choose minimum video time    
5. It will create a download folder to download twitch video and after it was uploaded to youtube it will deleted automatically.    
6. It will create a txt file named ***local_highlights_links.txt*** to record Url that haven't been uploaded.    
---
1. 輸入twitch名稱。
2. 登入Youtube帳號，登入完會創造一個***token.pickle***檔記錄登入資訊，如果需要換帳號請刪除他並重新登入。  
3. 選擇要上傳公開還是私人影片。  
4. 選擇影片最短長度，小於時間內的影片不會下載與上傳。(可用於過濾CLIP與精華片段)  
5. 程式會創建一個download資料夾，當前影片會在裡面下載與上傳，上船完後會自動刪除。  
6. 程式會創建一個***local_highlights_links.txt***檔，用於紀錄尚未上傳的影片Url。
## Note
1. You can't use python file to run this program since there's no ***client_secrets.json*** file which is necessary for youtube login.    
If you want to run it with python, you can contact me or [make a ***client_secrets.json*** file(google console youtube data api) by yourself.](https://console.cloud.google.com/)    
2. If progaram terminated midway, you can just run the program again but you need to type same limit time.
---
1. 因為未上傳***client_secrets.json***檔，所以python檔無法直接執行，需要執行python檔的話請連絡我或[使用google console建立youtube data api.](https://console.cloud.google.com/)    
2. 如果程式中途終止，可以重先執行程式，但請輸入一樣的影片長度值。

---
# Version2
## Usage
---
1. Add Gui, you can enter channel name, min_duration, choose upload in private/public easily in Gui.
2. You can choose what vidoeos you want to download/upload in video list now, and only the video which ***min_duration < video's duration < 12 hours*** will show on video list.
---
1. 新增了圖形化介面，可以在介面輸入twitch名稱、影片最短長度、選擇上傳為公開或私人。
2. 現在可以在影片清單選擇要上傳哪些影片，在影片清單會出現的影片為: ***最小影片時間 < 該影片時間 < 12小時*** 。
