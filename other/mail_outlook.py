import re
import time
import traceback

from exchangelib import DELEGATE, Account, Configuration, Credentials
import imaplib
import email
from email.header import decode_header
import poplib
from email.parser import BytesParser


def fetch_from_pop3(username: str, password: str):
    POP3_PORT = 995
    POP3_SERVER = "pop." + username.split("@")[1]

    if username.endswith("@outlook.com") or username.endswith("@hotmail.com"):
        POP3_SERVER = 'pop-mail.outlook.com'
    elif username.endswith('@gmail.com'):
        POP3_SERVER = 'pop.gmail.com'

    mail = poplib.POP3_SSL(POP3_SERVER, POP3_PORT)
    mail.user(username)
    mail.pass_(password)

    # Get the list of all messages (including Junk/Spam)
    response, lines, octets = mail.uidl()
    message_numbers = [line.split()[0].decode() for line in lines[1:]]

    code = ""
    verify_url = ""

    for msg_num in reversed(message_numbers):
        response, lines, octets = mail.retr(int(msg_num))
        msg_data = b'\r\n'.join(lines)
        msg = BytesParser().parsebytes(msg_data)

        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else 'utf-8')
        print("主题:", subject)

        body = ""
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
            elif part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode(errors="ignore")

            if "Verify" in subject:
                result = re.findall(r'href=\".*?\"', body)
                for link in result:
                    if "authentication" in link:
                        verify_url = link.replace('href=', "").replace('"', "").replace("&amp;", "&")

            if "verification" in subject or "TikTok code" in subject:
                code = subject.split(" ")[0]

            if len(code) > 0 and len(verify_url) > 0:
                break

        if len(code) > 0 and len(verify_url) > 0:
            print("中断!!")
            break

    mail.quit()
    ret = f"{code}|{verify_url}|pop3"
    print(ret)
    return ret


def fetch_tk_code_and_verify(username: str, password: str):
    return fetch_from_imap(username, password)


def fetch_from_outlook(username: str, password: str):
    config = Configuration(server='outlook.office365.com', credentials=Credentials(username, password),
                           auth_type='basic')
    account = Account(primary_smtp_address=username, config=config, autodiscover=False, access_type=DELEGATE)

    code = ""
    verify_url = ""

    for item in account.inbox.all().order_by('-datetime_received')[:10]:  # 检查最新的10封邮件
        if "Verify" in item.subject:
            result = re.findall(r'href=\".*?\"', item.body)
            for link in result:
                if "authentication" in link:
                    verify_url = link.replace('href=', "").replace('"', "").replace("&amp;", "&")
        if "verification" in item.subject:
            code = item.subject.split(" ")[0]
        if len(code) > 0 and len(verify_url) > 0:
            break

    account.protocol.close()
    ret = f"{code}|{verify_url}|outlook"
    print(f"{code}|{verify_url}")
    return ret


def fetch_from_imap(username: str, password: str):
    IMAP_PORT = 993
    IMAP_SERVER = "imap." + username.split("@")[1]

    if username.endswith("@outlook.com") or username.endswith("@hotmail.com"):
        IMAP_SERVER = 'imap-mail.outlook.com'  # 修改为适用于其他邮箱的IMAP服务器地址
    if username.endswith('@gmail.com'):
        IMAP_SERVER = 'imap.gmail.com'
    print("登录:", username)
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(username, password)

    folder_list = ['inbox', 'Junk', "Junk Email", 'Spam']  # 添加可能的垃圾箱文件夹名字
    code = ""
    verify_url = ""

    for folder in folder_list:
        try:
            mail.select(folder)
            status, messages = mail.search(None, 'ALL')
            if status != 'OK':
                continue

            emails = messages[0].split()

            for num in emails[::-1][:10]:  # 检查最新的10封邮件
                status, message_data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue
                msg = email.message_from_bytes(message_data[0][1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8')
                print(folder, "标题:", subject)
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                    elif part.get_content_type() == "text/html":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                    # 先判断是否为空再登录
                    if len(verify_url) < 10:
                        if "Verify" in subject:
                            result = re.findall(r'href=\".*?\"', body)
                            for link in result:
                                if "authentication" in link:
                                    verify_url = link.replace('href=', "").replace('"', "").replace("&amp;", "&")
                    # 先判断验证码是否存在
                    if len(code) < 3:
                        if " code" in subject or "TikTok code" in subject:
                            code = subject.split(" ")[0]
                    if len(code) > 0 or len(verify_url) > 0:
                        break

                if len(code) > 0 or len(verify_url) > 0:
                    break
        except imaplib.IMAP4.error:
            continue

        if len(code) > 0 and len(verify_url) > 0:
            break

    mail.logout()
    ret = f"{code}|{verify_url}|imap"
    print(ret)
    return ret


def remove_up_printable_chars(s):
    """移除所有不可见字符"""
    return ''.join(x for x in s if x.isprintable())


def handle_check_email(input_content: str) -> str:
    emails = input_content.split("\n")
    ct = ""
    for e in emails:
        if len(e) < 6:
            continue
        sp = remove_up_printable_chars(e).split("----")
        if len(sp) != 2:
            ct += e + "\t录入格式不当\t" + "\n"
            continue
        u = sp[0]
        p = sp[1]
        try:
            ret = fetch_tk_code_and_verify(u, p)
            if "|" in ret:
                ct += e + "\t登录成功\t" + ret + "\n"
            else:
                ct += e + "\t状态未知\t" + ret + "\n"
        except Exception as ex:
            ct += e + "\t登录异常\t" + repr(ex) + "\n"
    return ct


if __name__ == "__main__":
    # fetch_tk_code_and_verify("amffeq@hotmail.com", "05Fcc49dF")
    fetch_tk_code_and_verify(*"vyccygiin@outlook.com----goz486389".split("----"))