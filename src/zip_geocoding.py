"""
ZIP Code Geocoding, PADD Resolution & Unmapped Telemetry Engine (src/zip_geocoding.py)

Maps 5-digit US ZIP codes and 3-digit ZIP prefixes to supported metro area locales,
PADD regions, states, and state motor fuel tax policies with 100% offline fallback
and persistent telemetry logging for out-of-metro lookups (Issues #50 & #195).
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Base directory for data storage
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
TELEMETRY_FILE = os.path.join(DATA_DIR, "unmapped_zip_telemetry.json")

# Primary 3-digit ZIP prefix mapping for supported metro clusters
ZIP_METRO_PREFIX_MAP: Dict[str, str] = {
    "740": "tulsa", "741": "tulsa", "742": "tulsa", "743": "tulsa",
    "197": "newark", "198": "newark", "199": "newark",
    "450": "cincinnati", "451": "cincinnati", "452": "cincinnati",
    "278": "greenville", "279": "greenville",
    "280": "charlotte", "281": "charlotte", "282": "charlotte",
    "945": "oakland", "946": "oakland",
    "349": "port_st_lucie",
    "940": "bayarea", "941": "bayarea", "942": "bayarea", "943": "bayarea", "944": "bayarea"
}

# 3-digit ZIP prefix mapping to 2-letter state postal codes
ZIP_PREFIX_STATE_MAP: Dict[str, str] = {
    # PADD 1A (New England)
    "039": "ME", "040": "ME", "041": "ME", "042": "ME", "043": "ME", "044": "ME", "045": "ME", "046": "ME", "047": "ME", "048": "ME", "049": "ME",
    "030": "NH", "031": "NH", "032": "NH", "033": "NH", "034": "NH", "035": "NH", "036": "NH", "037": "NH", "038": "NH",
    "050": "VT", "051": "VT", "052": "VT", "053": "VT", "054": "VT", "056": "VT", "057": "VT", "058": "VT", "059": "VT",
    "010": "MA", "011": "MA", "012": "MA", "013": "MA", "014": "MA", "015": "MA", "016": "MA", "017": "MA", "018": "MA", "019": "MA", "020": "MA", "021": "MA", "022": "MA", "023": "MA", "024": "MA", "025": "MA", "026": "MA", "027": "MA",
    "028": "RI", "029": "RI",
    "060": "CT", "061": "CT", "062": "CT", "063": "CT", "064": "CT", "065": "CT", "066": "CT", "067": "CT", "068": "CT", "069": "CT",
    # PADD 1B (Central Atlantic)
    "100": "NY", "101": "NY", "102": "NY", "103": "NY", "104": "NY", "105": "NY", "106": "NY", "107": "NY", "108": "NY", "109": "NY", "110": "NY", "111": "NY", "112": "NY", "113": "NY", "114": "NY", "115": "NY", "116": "NY", "117": "NY", "118": "NY", "119": "NY", "120": "NY", "121": "NY", "122": "NY", "123": "NY", "124": "NY", "125": "NY", "126": "NY", "127": "NY", "128": "NY", "129": "NY", "130": "NY", "131": "NY", "132": "NY", "133": "NY", "134": "NY", "135": "NY", "136": "NY", "137": "NY", "138": "NY", "139": "NY", "140": "NY", "141": "NY", "142": "NY", "143": "NY", "144": "NY", "145": "NY", "146": "NY", "147": "NY", "148": "NY", "149": "NY",
    "150": "PA", "151": "PA", "152": "PA", "153": "PA", "154": "PA", "155": "PA", "156": "PA", "157": "PA", "158": "PA", "159": "PA", "160": "PA", "161": "PA", "162": "PA", "163": "PA", "164": "PA", "165": "PA", "166": "PA", "167": "PA", "168": "PA", "169": "PA", "170": "PA", "171": "PA", "172": "PA", "173": "PA", "174": "PA", "175": "PA", "176": "PA", "177": "PA", "178": "PA", "179": "PA", "180": "PA", "181": "PA", "182": "PA", "183": "PA", "184": "PA", "185": "PA", "186": "PA", "187": "PA", "188": "PA", "189": "PA", "190": "PA", "191": "PA", "192": "PA", "193": "PA", "194": "PA", "195": "PA", "196": "PA",
    "070": "NJ", "071": "NJ", "072": "NJ", "073": "NJ", "074": "NJ", "075": "NJ", "076": "NJ", "077": "NJ", "078": "NJ", "079": "NJ", "080": "NJ", "081": "NJ", "082": "NJ", "083": "NJ", "084": "NJ", "085": "NJ", "086": "NJ", "087": "NJ", "088": "NJ", "089": "NJ",
    "197": "DE", "198": "DE", "199": "DE",
    "206": "MD", "207": "MD", "208": "MD", "209": "MD", "210": "MD", "211": "MD", "212": "MD", "214": "MD", "215": "MD", "216": "MD", "217": "MD", "218": "MD", "219": "MD",
    "200": "DC", "202": "DC", "203": "DC", "204": "DC", "205": "DC",
    # PADD 1C (Lower Atlantic)
    "220": "VA", "221": "VA", "222": "VA", "223": "VA", "224": "VA", "225": "VA", "226": "VA", "227": "VA", "228": "VA", "229": "VA", "230": "VA", "231": "VA", "232": "VA", "233": "VA", "234": "VA", "235": "VA", "236": "VA", "237": "VA", "238": "VA", "239": "VA", "240": "VA", "241": "VA", "242": "VA", "243": "VA", "244": "VA", "245": "VA", "246": "VA",
    "247": "WV", "248": "WV", "249": "WV", "250": "WV", "251": "WV", "252": "WV", "253": "WV", "254": "WV", "255": "WV", "256": "WV", "257": "WV", "258": "WV", "259": "WV", "260": "WV", "261": "WV", "262": "WV", "263": "WV", "264": "WV", "265": "WV", "266": "WV", "267": "WV", "268": "WV",
    "270": "NC", "271": "NC", "272": "NC", "273": "NC", "274": "NC", "275": "NC", "276": "NC", "277": "NC", "278": "NC", "279": "NC", "280": "NC", "281": "NC", "282": "NC", "283": "NC", "284": "NC", "285": "NC", "286": "NC", "287": "NC", "288": "NC", "289": "NC",
    "290": "SC", "291": "SC", "292": "SC", "293": "SC", "294": "SC", "295": "SC", "296": "SC", "297": "SC", "298": "SC", "299": "SC",
    "300": "GA", "301": "GA", "302": "GA", "303": "GA", "304": "GA", "305": "GA", "306": "GA", "307": "GA", "308": "GA", "309": "GA", "310": "GA", "311": "GA", "312": "GA", "313": "GA", "314": "GA", "315": "GA", "316": "GA", "317": "GA", "318": "GA", "319": "GA", "398": "GA", "399": "GA",
    "320": "FL", "321": "FL", "322": "FL", "323": "FL", "324": "FL", "325": "FL", "326": "FL", "327": "FL", "328": "FL", "329": "FL", "330": "FL", "331": "FL", "332": "FL", "333": "FL", "334": "FL", "335": "FL", "336": "FL", "337": "FL", "338": "FL", "339": "FL", "341": "FL", "342": "FL", "344": "FL", "346": "FL", "347": "FL", "349": "FL",
    # PADD 2 (Midwest)
    "740": "OK", "741": "OK", "742": "OK", "743": "OK", "744": "OK", "745": "OK", "746": "OK", "747": "OK", "748": "OK", "749": "OK", "730": "OK", "731": "OK", "734": "OK", "735": "OK", "736": "OK", "737": "OK", "738": "OK", "739": "OK",
    "450": "OH", "451": "OH", "452": "OH", "453": "OH", "454": "OH", "455": "OH", "456": "OH", "457": "OH", "458": "OH", "430": "OH", "431": "OH", "432": "OH", "433": "OH", "434": "OH", "435": "OH", "436": "OH", "437": "OH", "438": "OH", "439": "OH", "440": "OH", "441": "OH", "442": "OH", "443": "OH", "444": "OH", "445": "OH", "446": "OH", "447": "OH", "448": "OH", "449": "OH",
    "600": "IL", "601": "IL", "602": "IL", "603": "IL", "604": "IL", "605": "IL", "606": "IL", "607": "IL", "608": "IL", "609": "IL", "610": "IL", "611": "IL", "612": "IL", "613": "IL", "614": "IL", "615": "IL", "616": "IL", "617": "IL", "618": "IL", "619": "IL", "620": "IL", "622": "IL", "623": "IL", "624": "IL", "625": "IL", "626": "IL", "627": "IL", "628": "IL", "629": "IL",
    "460": "IN", "461": "IN", "462": "IN", "463": "IN", "464": "IN", "465": "IN", "466": "IN", "467": "IN", "468": "IN", "469": "IN", "470": "IN", "471": "IN", "472": "IN", "473": "IN", "474": "IN", "475": "IN", "476": "IN", "477": "IN", "478": "IN", "479": "IN",
    "480": "MI", "481": "MI", "482": "MI", "483": "MI", "484": "MI", "485": "MI", "486": "MI", "487": "MI", "488": "MI", "489": "MI", "490": "MI", "491": "MI", "492": "MI", "493": "MI", "494": "MI", "495": "MI", "496": "MI", "497": "MI", "498": "MI", "499": "MI",
    "630": "MO", "631": "MO", "633": "MO", "634": "MO", "635": "MO", "636": "MO", "637": "MO", "638": "MO", "639": "MO", "640": "MO", "641": "MO", "644": "MO", "645": "MO", "646": "MO", "647": "MO", "648": "MO", "649": "MO", "650": "MO", "651": "MO", "652": "MO", "653": "MO", "654": "MO", "655": "MO", "656": "MO", "657": "MO", "658": "MO",
    "660": "KS", "661": "KS", "662": "KS", "664": "KS", "665": "KS", "666": "KS", "667": "KS", "668": "KS", "669": "KS", "670": "KS", "671": "KS", "672": "KS", "673": "KS", "674": "KS", "675": "KS", "676": "KS", "677": "KS", "678": "KS", "679": "KS",
    "680": "NE", "681": "NE", "683": "NE", "684": "NE", "685": "NE", "686": "NE", "687": "NE", "688": "NE", "689": "NE", "690": "NE", "691": "NE", "692": "NE", "693": "NE",
    "500": "IA", "501": "IA", "502": "IA", "503": "IA", "504": "IA", "505": "IA", "506": "IA", "507": "IA", "508": "IA", "509": "IA", "510": "IA", "511": "IA", "512": "IA", "513": "IA", "514": "IA", "515": "IA", "516": "IA", "520": "IA", "521": "IA", "522": "IA", "523": "IA", "524": "IA", "525": "IA", "526": "IA", "527": "IA", "528": "IA",
    "550": "MN", "551": "MN", "553": "MN", "554": "MN", "555": "MN", "556": "MN", "557": "MN", "558": "MN", "559": "MN", "560": "MN", "561": "MN", "562": "MN", "563": "MN", "564": "MN", "565": "MN", "566": "MN", "567": "MN",
    "530": "WI", "531": "WI", "532": "WI", "534": "WI", "535": "WI", "537": "WI", "538": "WI", "539": "WI", "540": "WI", "541": "WI", "542": "WI", "543": "WI", "544": "WI", "545": "WI", "546": "WI", "547": "WI", "548": "WI", "549": "WI", "580": "ND", "581": "ND", "582": "ND", "583": "ND", "584": "ND", "585": "ND", "586": "ND", "587": "ND", "588": "ND", "570": "SD", "571": "SD", "572": "SD", "573": "SD", "574": "SD", "575": "SD", "576": "SD", "577": "SD",
    "400": "KY", "401": "KY", "402": "KY", "403": "KY", "404": "KY", "405": "KY", "406": "KY", "410": "KY", "411": "KY", "412": "KY", "413": "KY", "414": "KY", "415": "KY", "416": "KY", "417": "KY", "418": "KY", "420": "KY", "421": "KY", "422": "KY", "423": "KY", "424": "KY", "425": "KY", "426": "KY", "427": "KY",
    "370": "TN", "371": "TN", "372": "TN", "373": "TN", "374": "TN", "376": "TN", "377": "TN", "378": "TN", "379": "TN", "380": "TN", "381": "TN", "382": "TN", "383": "TN", "384": "TN", "385": "TN",
    # PADD 3 (Gulf Coast)
    "770": "TX", "771": "TX", "772": "TX", "773": "TX", "774": "TX", "775": "TX", "776": "TX", "777": "TX", "778": "TX", "779": "TX", "780": "TX", "781": "TX", "782": "TX", "783": "TX", "784": "TX", "785": "TX", "786": "TX", "787": "TX", "788": "TX", "789": "TX", "750": "TX", "751": "TX", "752": "TX", "753": "TX", "754": "TX", "755": "TX", "756": "TX", "757": "TX", "758": "TX", "759": "TX", "760": "TX", "761": "TX", "762": "TX", "763": "TX", "764": "TX", "765": "TX", "766": "TX", "767": "TX", "768": "TX", "769": "TX", "790": "TX", "791": "TX", "792": "TX", "793": "TX", "794": "TX", "795": "TX", "796": "TX", "797": "TX", "798": "TX", "799": "TX",
    "700": "LA", "701": "LA", "703": "LA", "704": "LA", "705": "LA", "706": "LA", "707": "LA", "708": "LA", "710": "LA", "711": "LA", "712": "LA", "713": "LA", "714": "LA",
    "716": "AR", "717": "AR", "718": "AR", "719": "AR", "720": "AR", "721": "AR", "722": "AR", "723": "AR", "724": "AR", "725": "AR", "726": "AR", "727": "AR", "728": "AR", "729": "AR",
    "386": "MS", "387": "MS", "388": "MS", "389": "MS", "390": "MS", "391": "MS", "392": "MS", "393": "MS", "394": "MS", "395": "MS", "396": "MS", "397": "MS",
    "350": "AL", "351": "AL", "352": "AL", "354": "AL", "355": "AL", "356": "AL", "357": "AL", "358": "AL", "359": "AL", "360": "AL", "361": "AL", "362": "AL", "363": "AL", "364": "AL", "365": "AL", "366": "AL", "367": "AL", "368": "AL", "369": "AL",
    "870": "NM", "871": "NM", "873": "NM", "874": "NM", "875": "NM", "877": "NM", "878": "NM", "879": "NM", "880": "NM", "881": "NM", "882": "NM", "883": "NM", "884": "NM",
    # PADD 4 (Rocky Mountain)
    "800": "CO", "801": "CO", "802": "CO", "803": "CO", "804": "CO", "805": "CO", "806": "CO", "807": "CO", "808": "CO", "809": "CO", "810": "CO", "811": "CO", "812": "CO", "813": "CO", "814": "CO", "815": "CO", "816": "CO",
    "840": "UT", "841": "UT", "843": "UT", "844": "UT", "845": "UT", "846": "UT", "847": "UT",
    "820": "WY", "821": "WY", "822": "WY", "823": "WY", "824": "WY", "825": "WY", "826": "WY", "827": "WY", "828": "WY", "829": "WY", "830": "WY", "831": "WY",
    "590": "MT", "591": "MT", "592": "MT", "593": "MT", "594": "MT", "595": "MT", "596": "MT", "597": "MT", "598": "MT", "599": "MT",
    "832": "ID", "833": "ID", "834": "ID", "835": "ID", "836": "ID", "837": "ID", "838": "ID",
    # PADD 5 (West Coast)
    "900": "CA", "901": "CA", "902": "CA", "903": "CA", "904": "CA", "905": "CA", "906": "CA", "907": "CA", "908": "CA", "910": "CA", "911": "CA", "912": "CA", "913": "CA", "914": "CA", "915": "CA", "916": "CA", "917": "CA", "918": "CA", "919": "CA", "920": "CA", "921": "CA", "922": "CA", "923": "CA", "924": "CA", "925": "CA", "926": "CA", "927": "CA", "928": "CA", "930": "CA", "931": "CA", "932": "CA", "933": "CA", "934": "CA", "935": "CA", "936": "CA", "937": "CA", "938": "CA", "939": "CA", "940": "CA", "941": "CA", "942": "CA", "943": "CA", "944": "CA", "945": "CA", "946": "CA", "947": "CA", "948": "CA", "949": "CA", "950": "CA", "951": "CA", "952": "CA", "953": "CA", "954": "CA", "955": "CA", "956": "CA", "957": "CA", "958": "CA", "959": "CA", "960": "CA", "961": "CA",
    "980": "WA", "981": "WA", "982": "WA", "983": "WA", "984": "WA", "985": "WA", "986": "WA", "988": "WA", "989": "WA", "990": "WA", "991": "WA", "992": "WA", "993": "WA", "994": "WA",
    "970": "OR", "971": "OR", "972": "OR", "973": "OR", "974": "OR", "975": "OR", "976": "OR", "977": "OR", "978": "OR", "979": "OR",
    "890": "NV", "891": "NV", "893": "NV", "894": "NV", "895": "NV", "897": "NV", "898": "NV",
    "850": "AZ", "851": "AZ", "852": "AZ", "853": "AZ", "855": "AZ", "856": "AZ", "857": "AZ", "859": "AZ", "860": "AZ", "863": "AZ", "864": "AZ", "865": "AZ",
    "995": "AK", "996": "AK", "997": "AK", "998": "AK", "999": "AK",
    "967": "HI", "968": "HI"
}

# State to PADD & Calibrated Model fallback mapping
STATE_PADD_MODEL_MAP: Dict[str, Dict[str, Any]] = {
    "CA": {"padd": "PADD 5", "padd_name": "West Coast", "fallback_locale": "oakland", "fallback_model": "Oakland_CA (PADD 5 CARB)", "state_tax": 0.596},
    "OR": {"padd": "PADD 5", "padd_name": "West Coast", "fallback_locale": "oakland", "fallback_model": "Oakland_CA (PADD 5 CARB)", "state_tax": 0.400},
    "WA": {"padd": "PADD 5", "padd_name": "West Coast", "fallback_locale": "oakland", "fallback_model": "Oakland_CA (PADD 5 CARB)", "state_tax": 0.494},
    "NV": {"padd": "PADD 5", "padd_name": "West Coast", "fallback_locale": "oakland", "fallback_model": "Oakland_CA (PADD 5 CARB)", "state_tax": 0.505},
    "AZ": {"padd": "PADD 5", "padd_name": "West Coast", "fallback_locale": "oakland", "fallback_model": "Oakland_CA (PADD 5 CARB)", "state_tax": 0.180},
    "NY": {"padd": "PADD 1B", "padd_name": "Central Atlantic", "fallback_locale": "newark", "fallback_model": "Newark_DE (PADD 1B)", "state_tax": 0.472},
    "NJ": {"padd": "PADD 1B", "padd_name": "Central Atlantic", "fallback_locale": "newark", "fallback_model": "Newark_DE (PADD 1B)", "state_tax": 0.423},
    "PA": {"padd": "PADD 1B", "padd_name": "Central Atlantic", "fallback_locale": "newark", "fallback_model": "Newark_DE (PADD 1B)", "state_tax": 0.576},
    "DE": {"padd": "PADD 1B", "padd_name": "Central Atlantic", "fallback_locale": "newark", "fallback_model": "Newark_DE (PADD 1B)", "state_tax": 0.230},
    "MD": {"padd": "PADD 1B", "padd_name": "Central Atlantic", "fallback_locale": "newark", "fallback_model": "Newark_DE (PADD 1B)", "state_tax": 0.470},
    "NC": {"padd": "PADD 1C", "padd_name": "Lower Atlantic", "fallback_locale": "charlotte", "fallback_model": "Charlotte_NC (PADD 1C)", "state_tax": 0.404},
    "SC": {"padd": "PADD 1C", "padd_name": "Lower Atlantic", "fallback_locale": "charlotte", "fallback_model": "Charlotte_NC (PADD 1C)", "state_tax": 0.280},
    "FL": {"padd": "PADD 1C", "padd_name": "Lower Atlantic", "fallback_locale": "port_st_lucie", "fallback_model": "Port_St_Lucie_FL (PADD 1C)", "state_tax": 0.362},
    "GA": {"padd": "PADD 1C", "padd_name": "Lower Atlantic", "fallback_locale": "charlotte", "fallback_model": "Charlotte_NC (PADD 1C)", "state_tax": 0.312},
    "VA": {"padd": "PADD 1C", "padd_name": "Lower Atlantic", "fallback_locale": "charlotte", "fallback_model": "Charlotte_NC (PADD 1C)", "state_tax": 0.298},
    "OK": {"padd": "PADD 2", "padd_name": "Midwest", "fallback_locale": "tulsa", "fallback_model": "Tulsa_OK (PADD 2)", "state_tax": 0.190},
    "OH": {"padd": "PADD 2", "padd_name": "Midwest", "fallback_locale": "cincinnati", "fallback_model": "Cincinnati_OH (PADD 2)", "state_tax": 0.385},
    "IL": {"padd": "PADD 2", "padd_name": "Midwest", "fallback_locale": "cincinnati", "fallback_model": "Cincinnati_OH (PADD 2)", "state_tax": 0.454},
    "TX": {"padd": "PADD 3", "padd_name": "Gulf Coast", "fallback_locale": "national", "fallback_model": "National Wholesale (PADD 3)", "state_tax": 0.200},
    "LA": {"padd": "PADD 3", "padd_name": "Gulf Coast", "fallback_locale": "national", "fallback_model": "National Wholesale (PADD 3)", "state_tax": 0.200}
}


def resolve_zip_code(zip_code: str) -> Dict[str, Any]:
    """
    Resolves a 5-digit US ZIP code to mapped metro area locale, PADD region, state,
    state fuel tax, and resolution tier. Logs unmapped out-of-metro lookups.
    """
    zip_clean = str(zip_code).strip()[:5]
    if len(zip_clean) < 3 or not zip_clean.isdigit():
        return {
            "status": "fallback",
            "zip_code": zip_clean,
            "resolution_tier": "INVALID_INPUT_FALLBACK",
            "is_metro_cluster_hit": False,
            "locale_code": "national",
            "region_id": "National",
            "padd_region": "PADD 2 (Midwest)",
            "state": "US",
            "state_tax_rate_per_gal": 0.184
        }

    prefix_3 = zip_clean[:3]

    # Check Tier 1: Primary Metro Cluster Hit
    if prefix_3 in ZIP_METRO_PREFIX_MAP:
        metro_loc = ZIP_METRO_PREFIX_MAP[prefix_3]
        state_code = ZIP_PREFIX_STATE_MAP.get(prefix_3, "US")
        state_meta = STATE_PADD_MODEL_MAP.get(state_code, {})

        res = {
            "status": "success",
            "zip_code": zip_clean,
            "resolution_tier": "METRO_CLUSTER_HIT",
            "is_metro_cluster_hit": True,
            "locale_code": metro_loc,
            "prefix_3": prefix_3,
            "state": state_code,
            "padd_region": state_meta.get("padd", "PADD 2"),
            "state_tax_rate_per_gal": state_meta.get("state_tax", 0.250)
        }
        return res

    # Tier 2: State & PADD Resolution Fallback (Out-of-Metro Cluster)
    state_code = ZIP_PREFIX_STATE_MAP.get(prefix_3, "US")
    state_meta = STATE_PADD_MODEL_MAP.get(state_code, {
        "padd": "PADD 2", "padd_name": "Midwest", "fallback_locale": "national", "fallback_model": "National Wholesale", "state_tax": 0.250
    })

    res = {
        "status": "success",
        "zip_code": zip_clean,
        "resolution_tier": "STATE_PADD_FALLBACK",
        "is_metro_cluster_hit": False,
        "locale_code": state_meta.get("fallback_locale", "national"),
        "prefix_3": prefix_3,
        "state": state_code,
        "padd_region": state_meta.get("padd", "PADD 2"),
        "padd_name": state_meta.get("padd_name", "Midwest"),
        "calibrated_model_used": state_meta.get("fallback_model", "National Wholesale"),
        "state_tax_rate_per_gal": state_meta.get("state_tax", 0.250)
    }

    # Log telemetry for out-of-metro lookups
    try:
        log_unmapped_zip_lookup(zip_clean, res)
    except Exception as e:
        logger.warning(f"Error logging unmapped ZIP lookup for '{zip_clean}': {e}")

    return res


def log_unmapped_zip_lookup(zip_code: str, resolution: Dict[str, Any]) -> None:
    """
    Logs an unmapped out-of-metro ZIP code lookup to data/unmapped_zip_telemetry.json,
    incrementing query hit count and updating timestamps.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    data = {}
    if os.path.exists(TELEMETRY_FILE):
        try:
            with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Error reading {TELEMETRY_FILE}: {e}")
            data = {}

    now_iso = datetime.now().isoformat()
    z_key = str(zip_code)

    if z_key in data:
        data[z_key]["hit_count"] += 1
        data[z_key]["last_searched_at"] = now_iso
    else:
        data[z_key] = {
            "zip_code": z_key,
            "state": resolution.get("state", "US"),
            "padd_region": resolution.get("padd_region", "PADD 2"),
            "calibrated_model_used": resolution.get("calibrated_model_used", "National Wholesale"),
            "hit_count": 1,
            "first_searched_at": now_iso,
            "last_searched_at": now_iso
        }

    try:
        with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing to {TELEMETRY_FILE}: {e}")


def get_unmapped_zip_telemetry() -> Dict[str, Any]:
    """
    Returns aggregated unmapped ZIP code lookup telemetry, sorted by hit count,
    including state/PADD query distributions and recommended expansion metro hubs.
    """
    if not os.path.exists(TELEMETRY_FILE):
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_unmapped_queries": 0,
            "unique_unmapped_zips": 0,
            "top_unmapped_zips": [],
            "state_distribution": {},
            "recommended_expansion_hubs": []
        }

    try:
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading {TELEMETRY_FILE}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "top_unmapped_zips": []
        }

    records = list(data.values())
    records.sort(key=lambda x: x.get("hit_count", 0), reverse=True)

    total_queries = sum(r.get("hit_count", 0) for r in records)
    state_dist: Dict[str, int] = {}
    for r in records:
        st = r.get("state", "US")
        state_dist[st] = state_dist.get(st, 0) + r.get("hit_count", 0)

    # Recommend candidate hubs based on top states/ZIPs
    expansion_hubs = []
    if "IL" in state_dist:
        expansion_hubs.append({"metro": "Chicago Metro Area", "state": "IL", "padd": "PADD 2", "reason": f"High Midwest demand ({state_dist['IL']} lookups)"})
    if "TX" in state_dist:
        expansion_hubs.append({"metro": "Houston / Gulf Coast Metro", "state": "TX", "padd": "PADD 3", "reason": f"High Gulf refining demand ({state_dist['TX']} lookups)"})
    if "CA" in state_dist:
        expansion_hubs.append({"metro": "Greater Los Angeles Basin", "state": "CA", "padd": "PADD 5", "reason": f"High CARB retail demand ({state_dist['CA']} lookups)"})
    if "NY" in state_dist or "PA" in state_dist:
        expansion_hubs.append({"metro": "Greater Philadelphia & NYC Corridor", "state": "NY/PA", "padd": "PADD 1B", "reason": "High Central Atlantic rack demand"})

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total_unmapped_queries": total_queries,
        "unique_unmapped_zips": len(records),
        "top_unmapped_zips": records[:50],
        "state_distribution": state_dist,
        "recommended_expansion_hubs": expansion_hubs
    }
