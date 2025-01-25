from typing import Optional, List
from dataclasses import dataclass
import datetime
import pytz

import aiohttp
from bs4 import BeautifulSoup
import json
import imgkit
from io import BytesIO

import config
import database
from database.models import MailSession


class AuthError(Exception):
    pass

class RequestError(Exception):
    pass


@dataclass
class Mail:
    uid: int
    flags: List[str]
    from_email: str
    content_type: str
    send_datetime: datetime.datetime
    size: int
    title: Optional[str] = None
    from_name: Optional[str] = None


@dataclass
class Session:
    id: int
    is_my_session: bool
    login_address: str
    login_time: int
    protocol: str
    browser: str
    client_info: str
    platform: str
    is_tg_bot: bool


class Samoware:
    def __init__(self, mail_session: MailSession):
        self.mail_session = mail_session

        self.api_path = "https://student.bmstu.ru"
        self.open_inbox_folder_id = 99
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.aiohttp_session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
        self.aiohttp_session.headers.update({
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "ru-RU,ru;q=0.9,en-GB;q=0.8,en;q=0.7,en-US;q=0.6",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/xml;charset=UTF-8",
            "DNT": "1",
            "Host": "student.bmstu.ru",
            "Origin": "https://student.bmstu.ru",
            "Pragma": "no-cache",
            "Referer": "https://student.bmstu.ru/",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        })
        self.update_cookies()
        return self

    def update_cookies(self):
        if self.mail_session.cookie_session is not None:
            self.aiohttp_session.cookie_jar.update_cookies({"CGateProWebUser": self.mail_session.cookie_session})

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aiohttp_session.close()
        self.aiohttp_session = None

    async def auth(self):
        params = {
            "errorAsXML": "1",
            "EnableUseCookie": "1",
            "x2auth": "1",
            "canUpdatePwd": "1",
            "userName": self.mail_session.login,
            "password": self.mail_session.password,
            "killOld": "1"
        }
        headers = {
            "Content-Type": ""
        }
        async with self.aiohttp_session.get(self.api_path + "/XIMSSLogin/", params=params, headers=headers) as response:
            response_xml = BeautifulSoup(await response.text(), 'lxml')
            if ((response_elem := response_xml.find("response")) is not None) and ((error_code := response_elem.get('errornum')) is not None):
                raise AuthError(f"Invalid login or password (code={error_code})")

            session_elem = response_xml.find("session")
            self.mail_session.update_session_at = datetime.datetime.now(tz=pytz.UTC) + datetime.timedelta(hours=1)
            self.mail_session.url_id = session_elem.get("urlid")
            self.mail_session.email = session_elem.get("username")
            self.mail_session.full_name = session_elem.get("realname")
            self.aiohttp_session.cookie_jar.clear()

    async def logout(self):
        data = f"""<XIMSS><bye id="99"/></XIMSS>"""
        async with self.aiohttp_session.post(self.api_path + f"/Session/{self.mail_session.url_id}/sync", data=data) as response:
            print("LOGOUT:", response.status)

    async def get_active_sessions(self) -> List[Session]:
        data = aiohttp.FormData()
        data.add_field("op", "getSessionsInfo")
        data.add_field("session", self.mail_session.url_id)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://student.bmstu.ru/"
        }
        async with self.aiohttp_session.post(self.api_path + "/sys/sessionadmin.wcgp", data=data, headers=headers) as response:
            if response.status != 200:
                raise RequestError(f"Error while getting active sessions (status={response.status})")
            return [
                Session(
                    id=int(session["id"]),
                    is_my_session=session.get("isMySession", False),
                    login_address=session["loginAddress"],
                    login_time=int(session["loginTime"]),
                    protocol=session["protocol"],
                    browser=session.get("sessionInfo", dict()).get("browser"),
                    client_info=session.get("sessionInfo", dict()).get("clientInfo"),
                    platform=session.get("sessionInfo", dict()).get("platform"),
                    is_tg_bot=session.get("sessionInfo", dict()).get("is_tg_bot", False) == "true"
                )
                for session in json.loads(await response.text())["activeSessions"]
            ]

    async def close_session(self, session_id: int):
        data = aiohttp.FormData()
        data.add_field("op", "removeSessions")
        data.add_field("id", str(session_id))
        data.add_field("session", self.mail_session.url_id)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://student.bmstu.ru/"
        }
        async with self.aiohttp_session.post(self.api_path + "/sys/sessionadmin.wcgp", data=data, headers=headers) as response:
            if response.status != 200:
                raise RequestError(f"Error while removing session (status={response.status})")

    async def send_session_info(self):
        data = aiohttp.FormData()
        data.add_field("op", "setSessionInfo")
        data.add_field("paramType", "json")
        data.add_field("param", f'{{"clientName":"{config.SAMOWARE_CLIENT_NAME}","is_tg_bot":"true"}}')
        data.add_field("session", self.mail_session.url_id)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        async with self.aiohttp_session.post(self.api_path + f"/Session/{self.mail_session.url_id}/sessionadmin.wcgp", data=data, headers=headers) as response:
            if response.status != 200:
                raise RequestError(f"Error while sending session info (status={response.status})")

    async def open_folder(self):
        data = f"""<XIMSS>
                    <folderOpen mailbox="INBOX" sortField="INTERNALDATE" sortOrder="desc" folder="INBOX-MM-1" id="{self.open_inbox_folder_id}">
                        <field>FLAGS</field>
                        <field>E-From</field>
                        <field>Subject</field>
                        <field>Content-Type</field>
                        <field>INTERNALDATE</field>
                        <field>SIZE</field>
                        <field>E-To</field>
                        <field>Message-ID</field>
                    </folderOpen>
                </XIMSS>"""
        async with self.aiohttp_session.post(self.api_path + f"/Session/{self.mail_session.url_id}/sync", data=data) as response:
            if response.status == 550:
                raise AuthError("Session expired")
            if response.status != 200:
                raise RequestError(f"Error while opening folder (status={response.status})")
            if "CGateProWebUser" in response.cookies:
                self.mail_session.cookie_session = response.cookies.get("CGateProWebUser").value
                self.update_cookies()

    async def get_last_mail(self, from_datetime: datetime.datetime = None) -> List[Mail]:
        data = f"""<XIMSS><folderBrowse folder="INBOX-MM-1" id="{self.open_inbox_folder_id}"><index from="0" till="49"/></folderBrowse></XIMSS>"""
        async with self.aiohttp_session.post(self.api_path + f"/Session/{self.mail_session.url_id}/sync", data=data) as response:
            if response.status == 550:
                raise AuthError("Session expired")
            response_xml = BeautifulSoup(await response.text(), 'lxml')
            return list(filter(lambda t: ("Seen" not in t.flags) and ((from_datetime is None) or t.send_datetime >= from_datetime), [
                Mail(
                    uid=int(mail_elem.get("uid")),
                    flags=mail_elem.find("flags").text.split(","),
                    from_name=mail_elem.find("e-from").get("realname"),
                    from_email=mail_elem.find("e-from").text,
                    title=(lambda t: t.text if (t is not None) else None)(mail_elem.find("subject")),
                    content_type=mail_elem.find("content-type").text,
                    send_datetime=datetime.datetime.strptime(mail_elem.find("internaldate").text, '%Y%m%dT%H%M%SZ'),
                    size=int(mail_elem.find("size").text)
                )
                for mail_elem in response_xml.find_all("folderreport")
                if mail_elem.find("e-from") is not None
            ]))

    # async def sync_mail(self):
    #     data = f"""<XIMSS><folderSync folder="INBOX-MM-1" limit="300" id="{self.open_inbox_folder_id}"></folderSync></XIMSS>"""
    #     async with self.aiohttp_session.post(self.api_path + f"/Session/{self.mail_session.url_id}/sync", data=data) as response:
    #         if response.status == 550:
    #             raise AuthError("Session expired")
    #         response_xml = BeautifulSoup(await response.text(), 'lxml')
    #         mail_elems = response_xml.find_all("folderreport", {"mode": "added"})
    #         if len(mail_elems) == 0:
    #             return None
    #         mail_elem = max(mail_elems, key=lambda t: int(t.get("uid")))
    #
    #         return Mail(
    #             uid=int(mail_elem.get("uid")),
    #             flags=mail_elem.find("flags").text,
    #             from_name=mail_elem.find("e-from").get("realname"),
    #             from_email=mail_elem.find("e-from").text,
    #             title=mail_elem.find("subject").text,
    #             content_type=mail_elem.find("content-type").text,
    #             send_datetime=datetime.datetime.strptime(mail_elem.find("internaldate").text, '%Y%m%dT%H%M%SZ'),
    #             size=int(mail_elem.find("size").text)
    #         )

    async def get_mail_image(self, mail_id) -> BytesIO:
        async with self.aiohttp_session.get(self.api_path + f"/Session/{self.mail_session.url_id}/FORMAT/Samoware/INBOX-MM-1/{mail_id}") as response:
            html_text = await response.text()
            options = {
                'format': "PNG",
                'quality': 100,
                'encoding': "UTF-8",
                'quiet': ""
            }
            soup = BeautifulSoup(html_text, 'lxml')
            soup.find("table", {"class": "rfcheader"}).extract()
            for attachment_elem in soup.find_all("cg-message-attachment"):
                attachment_elem.extract()

            file = imgkit.from_string(soup.prettify(), False, options=options)
            ret = BytesIO()
            ret.write(file)
            ret.seek(0)
            return ret

    async def delete_mail(self, mail_id):
        data = f"""<XIMSS><messageRemove folder="INBOX-MM-1" id="{self.open_inbox_folder_id}"><UID>{mail_id}</UID></messageRemove></XIMSS>"""
        async with self.aiohttp_session.post(self.api_path + f"/Session/{self.mail_session.url_id}/sync", data=data) as response:
            if response.status != 200:
                raise RequestError(f"Error while deleting mail (status={response.status})")

    async def read_mail(self, mail_id):
        data = f"""<XIMSS><messageMark flags="Read" folder="INBOX-MM-1" id="{self.open_inbox_folder_id}"><UID>{mail_id}</UID></messageMark></XIMSS>"""
        async with self.aiohttp_session.post(self.api_path + f"/Session/{self.mail_session.url_id}/sync", data=data) as response:
            if response.status != 200:
                raise RequestError(f"Error while reading mail (status={response.status})")


async def test():
    db = database.Database()
    async with db.session() as db_session:
        mail_session = await db_session.scalar(
            database.select(database.models.MailSession)
            .where(database.models.MailSession.id == 2)
        )
        async with Samoware(mail_session=mail_session) as samoware:
            # await samoware.auth()
            # await samoware.send_session_info()
            # await samoware.open_folder()
            # await db_session.merge(mail_session)
            # await db_session.commit()
            print(await samoware.get_last_mail())


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.run(test())
