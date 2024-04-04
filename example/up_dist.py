import os
import shutil
import requests

# C:\Users\Administrator\Desktop\yy_docs 改为你的dist输出目录
shutil.make_archive("build", "zip", r"C:\Users\Administrator\Desktop\yy_docs")
files = {'file': open('build.zip', 'rb')}
res = requests.post("http://http://43.224.152.122:5031/post-files", files=files)
if res.status_code == 200:
    print("上传到服务器成功")
else:
    print("上传到服务器失败")
os.remove("build.zip")