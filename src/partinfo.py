
import json 
import dataclasses
import aiohttp
from PIL import Image
import io

from .api_keys import MOUSER_API_KEY

@dataclasses.dataclass
class PriceStep:
    price: float
    quantity: int

@dataclasses.dataclass
class PartInfo:
    description: str
    in_stock: int
    min_qty: int
    qty_multiples: int
    manufacturer: str
    manufacturer_part_number: str
    supplier_part_number: str
    currency: str
    price_breaks: list[PriceStep]
    packaging_options: list[str]
    details_url: str
    image_url: str
    image: Image.Image | None = None


async def request_part_info_mouser(code_data: bytes) -> PartInfo | None:
    # extract manufacturer part number from EICA code
    if not b'[)>' in code_data:
        print("Invalid code, returning None")
        return None
    
    code_components = code_data.split(r"".encode())
    # 3rd component is supplier part number, except the first two character which define the component
    mouser_part_number = code_components[3][2:]
    print(f"{mouser_part_number=}")
    
    part_info: PartInfo = ...
    async with aiohttp.ClientSession() as session:

        async with session.post(
            url=f"https://api.mouser.com/api/v1/search/partnumber?apiKey={MOUSER_API_KEY}",
            headers = {
                'Content-Type': "application/json",
                'accept': "application/json"
            },
            data=b"{\"SearchByPartRequest\": {\"mouserPartNumber\": \"" + mouser_part_number + b"\",}}"
        ) as response:
            if response.status != 200:
                print(f"API reponded with {response.status}")
                return None
            # This would be nice to do with pydantic but I'm not gonna bother with that now
            resp_data = await response.json()
            if len(resp_data["Errors"]) != 0:
                print(f"API returned some error(s): {resp_data["Errors"]}")
                return None
            search_results: dict = resp_data["SearchResults"]
            nr_results: int = search_results["NumberOfResult"]

            # get the part descriptor
            part_descriptor: dict = ...
            if nr_results == 0:
                print(f"No matching parts found on Mouser")
            
                return None
            elif nr_results == 1:
                part_descriptor = search_results["Parts"][0]
            else:
                # sometimes there are two equal parts, one only in full reels and one as cut tape.
                # So we select the one which has the lower minimum quantity (or the one that hay
                # any quantity at all)
                # possible alternatives: larger amount of price breaks, larger amount of packaging options, product status
                options: list[dict] = search_results["Parts"]
                options.reverse()
                print(f"Multiple parts found, arbitrating")
                # filter any parts with zero minimum count, these are not available
                options = [option for option in options if int(option["Min"]) > 0]
                # select the one with the smallest minimum order quantity
                part_descriptor = min(options, key=lambda o: int(o["Min"]) )
            
            print(f"found part:\n{json.dumps(part_descriptor, indent=3, sort_keys=True)}")
            part_info = PartInfo(
                description=                part_descriptor["Description"],
                in_stock=                   int(part_descriptor["AvailabilityInStock"]),
                min_qty=                    int(part_descriptor["Min"]),
                qty_multiples=              int(part_descriptor["Mult"]),
                manufacturer=               part_descriptor["Manufacturer"],
                manufacturer_part_number=   part_descriptor["ManufacturerPartNumber"],
                supplier_part_number=       part_descriptor["MouserPartNumber"],
                currency=                   part_descriptor["PriceBreaks"][0]["Currency"] if len(part_descriptor["PriceBreaks"]) else "N/A",
                price_breaks=               [
                    PriceStep(float("".join([c for c in brk["Price"] if c in "0123456789,."]).replace(",", ".")), int(brk["Quantity"]))
                    for brk in part_descriptor["PriceBreaks"]
                ],
                packaging_options=          [opt["AttributeValue"] for opt in part_descriptor["ProductAttributes"] if opt["AttributeName"] == "Packaging"],
                details_url=                part_descriptor["ProductDetailUrl"],
                image_url=                  part_descriptor["ImagePath"]
            )

    # also fetch the image
    print("beforesession")
    async with aiohttp.ClientSession() as session:
        print("insession")
        async with session.get(
            url=part_info.image_url,
            headers={
                # using some browser User agent because it doesn't work otherwise
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
                "Accept": "image/*",
                #"Accept-Language": "en-US,en;q=0.5",
                #"Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                #"Cookie": "preferences=FF=Feature_InvalidateSessionsLogic_Enable&pl=de-DE&pc_at=EUR&pc_eu=EUR&ps=; _abck=0FD5EE9F6F6B1075ACC032E484DA9E07~-1~YAAQGE4SAsaqgW2QAQAAIUrdiQyvjzLhwAPtLZlUfidU7uIUN6q5ZQec1TaNU6zwumegjjmxQQW3v69Zc0rpEyzGfSnopyJAN0qEbZX0vqatIYgWZSPhvXnJ1h52P5t4WzEhHJhr2cqukoi0tZIT6BnatDJ/obilgGi/SG5wxixsotNs2CXajwh509Ec+Zbc5c7QfT7DVnNnsWcSOyedkKvVsviD+tgoFfTGDlnzb7bQ4o+dkJ/GXDoWsX69RqNwxAaLboZDXguakTGRMsbpC1ORjc5pmBDh0oe76TlNIMUoS5NO5ps9MPzVGw59huss91RXdMrxCEhMLepd0duBAqsOD6AIj9PC9FpyYoYgsHzQi5lqUwuQZeSCNBK9lVH5vHx6Y/QlxZgyffcbVMln8SuhKDDIsxlcMcj43rafnK3EYw==~-1~-1~-1; datadome=lqeYQbOzkD2vkvSbBnQ19p79GP91nQa5WbUkcnGFaijWAcaG~SLpl9DpUv~LF6hsbmX8B9lHbrGjb5dq4qhr846Kptcc_3z9LDyAkkr5hExmSlL9DaKl8~neO9ghZVG0; CARTCOOKIEUUID=ed16f4f6-7d91-481f-8981-0b010914caf2; OptanonConsent=isGpcEnabled=0&datestamp=Sat+Jul+06+2024+23%3A02%3A49+GMT%2B0200+(Central+European+Summer+Time)&version=202403.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=5623e039-3240-4e40-a8f1-91cea2997f0e&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0004%3A1&AwaitingReconsent=false&geolocation=AT%3B7&isAnonUser=1; LPVID=U0Y2YxYjA1MDQzODZjYWQz; OptanonAlertBoxClosed=2024-02-13T10:35:19.389Z; _ga_15W4STQT4T=GS1.1.1720299763.6.1.1720299906.47.0.0; _ga=GA1.1.695587052.1707820520; _ga_1KQLCYKRX3=GS1.1.1709648528.2.0.1709648533.0.0.0; _ga_P029W6H4P4=GS1.1.1720299763.5.0.1720299768.0.0.0; _gcl_au=1.1.1781667644.1717887154; _fbp=fb.1.1717887155186.197634478609803516; fs_uid=#Z1BBJ#f2f192b5-5d24-4f34-b043-1fd12b822300:060e5961-0975-45a0-9cf2-14baea69c51b:1720299764453::2#/1739356540; _gid=GA1.2.36464325.1720219210; RT=\"z=1&dm=mouser.com&si=59a44931-4f98-41cb-9ff7-a19fd1715321&ss=lyam26q1&sl=2&tt=2yk&bcn=%2F%2F02179915.akstat.io%2F&ld=8g3&ul=34jx&hd=34nl\"; ASP.NET_SessionId=sdfezy0lm3foskchm2kg5bn4; akacd_Default_PR=3895919023~rv=26~id=ba6c6550f8f2311826153d06055d649f; akacd_PIM-prd_ah_rollout=3895919026~rv=88~id=354201410d225de1b5617308d024337a; __RequestVerificationToken=1hK7U054MEoZejyVdb7FEiOt2-pMmh-fVvf6R0WoSfoW8JeGdsRde2W9-qoWcSVGFfaNbMJEaCEV9Fr8e-kAKICwvlA1; PIM-SESSION-ID=HW1eZ9Bkh15eKJBQ; LPSID-12757882=o72tfw9HQmKXkfyzBRj3Ng; __AntiXsrfToken=af9cb0fc79c0414e925da9ecfcfda873; bm_sz=B68EE259F1219F6AF1CED3E775DC3652~YAAQGE4SAuxQdm2QAQAA9f+KiRgtc+UUwPam1CECYqDNqZDZVD+869rJbma5GgeszoPQ1b1BLKRTrTu0wU59ecrE2j7wBSbFZIdXIigkAYVEoyUBx9IzIVsVOmC26W8vyNy/FGaAYvyvIVfP2co2SHH2zVCWuv5GUIBQiakiqobzP0k2hFv6L+GZ2L024sFPIMQINaQzswiYB/xpdNq+JBXjDemUHJjkM2G3DWCB3E92MNtndoegm4PGhxTNUIycwuSsqwM58dmjiqTmf08OVrrumj/+qxIeeWAlOx/zidA7eWTzHvdGWIcE+pXJrfEmTXSUxHaTMpr1j9K05G6cS0/SmnceuVQ+GIUUxj7hT6vOYdxmdUhf6O6SA14X9D6BFLTwe3LwHT5IH9RlqwYrqGD2T6IYgkDyU41fBSyOD0BkY7XYafw=~3491128~4470325; AKA_A2=A; ak_bmsc=F88B620512A8D298A59F12E2DD298E95~000000000000000000000000000000~YAAQGE4SAt1pgW2QAQAAYzXbiRhVaPhFmWHup4BILL2zyKmcIPptU2Lf0+VvjRzzZSUshV+4kSZ5V9VWIo7IBOHogkTxiwhSDJi6quQP3bkjFg8FhI71cBxIBZLcJQFCpeXLIjppPKvBTwwmIZS0VoMuTiGJjl11ip/jKulYluYGt9muqNH7/GKsw4xYjLYi2aPnue/RBWJ1aXGMNUlA82P0VQYly1TGLc9QQC8BiyOoHvWzEmSZlCZhq3YIVkphwjk/j0IYCR4u5SHNJuqp3Ow62Wvu8idqjFQq8WbxgW0BVbkaqYWthUUYjQ9xfID9KBRDz8wov3B0JI95o//wj2sGEiJMr4XnvoZGplKelRcj3QfZmPAHzh5bqym6O54rktMIyPvZP3LybjRgP2lRPEh8itLi1KAlY3iWcydBZOfx7e8KDnJiyl8u6w/EmUGUgIrng5OdAC+vhIkQEoB6iUYShFHHkAmTSlg6rwkLyYGoOe+jxu4=; bm_mi=1D5D6479925F3CE377DDDAC18FCE44C2~YAAQGE4SAt5ogW2QAQAAIy/biRgn4NqehpC9yByFPpWmH1IXflICMbiO2fhAkLFQIkkGWTKnW7ev3MibrTTSlR9OizxpQYgC6XrcrY10wFZXPzqVpLqRk9tuOqXKrJYwOZPzIP1Wg21YU9NbNugA0NJXSnBhXt10mLA8h+slwQGK7pBJbxmUlkXtI0ug4wzxwi4agYpsYiz9gyKzMhJqoP3UGcM3VBePmRE0rtgP+0rWTnuS2yOWCZ4R24NcY0NmEiN5zcYJSb+DTTadHa75GDBTFdUWWet7yX5rp15sNAK0W39CJG9jQ2spqgen5rgE0xRPIa8=~1; fs_lua=1.1720299769987; _rdt_uuid=1717887154899.e0379250-b28e-4300-b301-720b4e1ae4ee",
                #"Upgrade-Insecure-Requests": "1",
                #"Sec-Fetch-Dest": "document",
                #"Sec-Fetch-Mode": "navigate",
                #"Sec-Fetch-Site": "none",
                #"Sec-Fetch-User": "?1",
                "Priority": "u=1",
                #"Pragma": "no-cache",
                #"Cache-Control": "no-cache"
            }
        ) as response:
            print("response herer")
            if (response.status) == 200:
                print("beforeopen")
                part_info.image = Image.open(io.BytesIO(await response.read()))
                print("after read")
            else:
                part_info.image = None
                
    return part_info
                
            

            
