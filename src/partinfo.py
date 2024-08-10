"""
ELEKTRON (c) 2024 - now
Written by melektron
www.elektron.work
06.07.24 11:51

API part info getters
"""

import dataclasses
import requests
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
    image_url: str | None
    image: Image.Image | None = None


def request_part_info_mouser(code_data: bytes) -> PartInfo | None:
    # extract manufacturer part number from EICA code
    if not b'[)>' in code_data:
        print("Invalid code, returning None")
        return None
    
    code_components = code_data.split(r"".encode())
    # 3rd component is supplier part number, except the first two character which define the component
    mouser_part_number = code_components[3][2:]
    print(f"{mouser_part_number=}")
    
    part_info: PartInfo = ...

    response: requests.Response = requests.post(
        url=f"https://api.mouser.com/api/v1/search/partnumber?apiKey={MOUSER_API_KEY}",
        headers = {
            'Content-Type': "application/json",
            'accept': "application/json"
        },
        data=b"{\"SearchByPartRequest\": {\"mouserPartNumber\": \"" + mouser_part_number + b"\",}}"
    )
    if response.status_code != 200:
        print(f"API reponded with {response.status_code}")
        return None
    # This would be nice to do with pydantic but I'm not gonna bother with that now
    resp_data = response.json()
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
    
    #print(f"found part:\n{json.dumps(part_descriptor, indent=3, sort_keys=True)}")
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

    # also fetch the image if available
    if part_info.image_url is None:
        part_info.image = None
        return part_info
    
    response: requests.Response = requests.get(
        url=part_info.image_url,
        headers={
            # using some browser User agent because it doesn't work otherwise
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
            "Accept": "image/*",
            "Connection": "keep-alive",
        }
    )
    if (response.status_code) == 200:
        part_info.image = Image.open(io.BytesIO(response.content))
    else:
        part_info.image = None
                
    return part_info
                
            

            
