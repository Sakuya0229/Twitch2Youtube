# Twitch2Youtube
This program can download twitch hightlight and upload to youtube one by one automatically.
## Installation
download exe file from google drive
<https://drive.google.com/file/d/1dEMCny2FB0meWITFs7IftwfrNqFKEzwy/view?usp=drive_link>
## Usage
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
You can't use python file to run this program since there's no ***client_secrets.json*** file which is necessary for youtube login.
If you want to run it with python, you can contact me or [make a ***client_secrets.json*** file(google console youtube data api) by yourself.]<https://console.cloud.google.com/>    
If progaram terminated midway, you can just run the program again but you need to type same limit time.  
---
因為未上傳***client_secrets.json***檔，所以python檔無法直接執行，需要執行python檔的話請連絡我或[使用google console建立youtube data api.]<https://console.cloud.google.com/>    
如果程式中途終止，可以重先執行程式，但請輸入一樣的影片長度值。
