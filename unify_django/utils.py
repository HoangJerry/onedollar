# coding=utf-8

import random
import string
from math import sin, cos, radians, acos

from django.conf import settings

EARTH_RADIUS = 6371


def login_user(request, user):
    """
    Log in a user without requiring credentials (using ``login`` from
    ``django.contrib.auth``, first finding a matching backend).

    """
    from django.contrib.auth import load_backend, login

    if not hasattr(user, 'backend'):
        for backend in settings.AUTHENTICATION_BACKENDS:
            if user == load_backend(backend).get_user(user.pk):
                user.backend = backend
                break

    if hasattr(user, 'backend'):
        return login(request, user)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def get_distance_query(lat, lon):
    return """
        ACOS(
            SIN(RADIANS(%(lat)s)) * SIN(RADIANS(latitude)) + 
            COS(RADIANS(%(lat)s)) * COS(RADIANS(latitude)) * 
            COS(RADIANS(%(lon)s - longitude))
        ) * %(radius)s
    """ % {"lat": lat, "lon": lon, "radius": EARTH_RADIUS}


def get_nearby_filter_query(lat, lon, distance):
    return "latitude <> 0 and longitude <> 0 AND (%s) <= %f" % (get_distance_query(lat, lon), distance)


def get_distance(lat1, lon1, lat2, lon2):
    rad_lat1 = radians(lat1)
    rad_lon1 = radians(lon1)
    rad_lat2 = radians(lat2)
    rad_lon2 = radians(lon2)

    return acos(
        sin(rad_lat1) * sin(rad_lat2) + cos(rad_lat1) * cos(rad_lat2) * cos(radians(lon1 - lon2))) * EARTH_RADIUS


def generate_random_string(digit_length=5, char_length=5):
    digits = "".join([random.choice(string.digits) for i in xrange(digit_length)])
    chars = "".join([random.choice(string.letters) for i in xrange(char_length)])
    return digits + chars


def convert_facebook_country_to_code(country):
    data = {
        'united states': 'US',
        'canada': 'CA',
        'united kingdom': 'GB',
        'argentina': 'AR',
        'australia': 'AU',
        'austria': 'AT',
        'belgium': 'BE',
        'brazil': 'BR',
        'chile': 'CL',
        'china': 'CN',
        'colombia': 'CO',
        'croatia': 'HR',
        'denmark': 'DK',
        'dominican republic': 'DO',
        'egypt': 'EG',
        'finland': 'FI',
        'france': 'FR',
        'germany': 'DE',
        'greece': 'GR',
        'hong kong': 'HK',
        'india': 'IN',
        'indonesia': 'ID',
        'ireland': 'IE',
        'israel': 'IL',
        'italy': 'IT',
        'japan': 'JP',
        'jordan': 'JO',
        'kuwait': 'KW',
        'lebanon': 'LB',
        'malaysia': 'MY',
        'mexico': 'MX',
        'netherlands': 'NL',
        'new zealand': 'NZ',
        'nigeria': 'NG',
        'norway': 'NO',
        'pakistan': 'PK',
        'panama': 'PA',
        'peru': 'PE',
        'philippines': 'PH',
        'poland': 'PL',
        'russia': 'RU',
        'saudi arabia': 'SA',
        'serbia': 'RS',
        'singapore': 'SG',
        'south africa': 'ZA',
        'south korea': 'KR',
        'spain': 'ES',
        'sweden': 'SE',
        'switzerland': 'CH',
        'taiwan': 'TW',
        'thailand': 'TH',
        'turkey': 'TR',
        'united arab emirates': 'AE',
        'venezuela': 'VE',
        'portugal': 'PT',
        'luxembourg': 'LU',
        'bulgaria': 'BG',
        'czech republic': 'CZ',
        'slovenia': 'SI',
        'iceland': 'IS',
        'slovakia': 'SK',
        'lithuania': 'LT',
        'trinidad and tobago': 'TT',
        'bangladesh': 'BD',
        'sri lanka': 'LK',
        'kenya': 'KE',
        'hungary': 'HU',
        'morocco': 'MA',
        'cyprus': 'CY',
        'jamaica': 'JM',
        'ecuador': 'EC',
        'romania': 'RO',
        'bolivia': 'BO',
        'guatemala': 'GT',
        'costa rica': 'CR',
        'qatar': 'QA',
        'el salvador': 'SV',
        'honduras': 'HN',
        'nicaragua': 'NI',
        'paraguay': 'PY',
        'uruguay': 'UY',
        'puerto rico': 'PR',
        'bosnia and herzegovina': 'BA',
        'palestine': 'PS',
        'tunisia': 'TN',
        'bahrain': 'BH',
        'vietnam': 'VN',
        'ghana': 'GH',
        'mauritius': 'MU',
        'ukraine': 'UA',
        'malta': 'MT',
        'the bahamas': 'BS',
        'maldives': 'MV',
        'oman': 'OM',
        'macedonia': 'MK',
        'latvia': 'LV',
        'estonia': 'EE',
        'iraq': 'IQ',
        'algeria': 'DZ',
        'albania': 'AL',
        'nepal': 'NP',
        'macau': 'MO',
        'montenegro': 'ME',
        'senegal': 'SN',
        'georgia': 'GE',
        'brunei': 'BN',
        'uganda': 'UG',
        'guadeloupe': 'GP',
        'barbados': 'BB',
        'azerbaijan': 'AZ',
        'tanzania': 'TZ',
        'libya': 'LY',
        'martinique': 'MQ',
        'cameroon': 'CM',
        'botswana': 'BW',
        'ethiopia': 'ET',
        'kazakhstan': 'KZ',
        'namibia': 'NA',
        'madagascar': 'MG',
        'new caledonia': 'NC',
        'moldova': 'MD',
        'fiji': 'FJ',
        'belarus': 'BY',
        'jersey': 'JE',
        'guam': 'GU',
        'yemen': 'YE',
        'zambia': 'ZM',
        'isle of man': 'IM',
        'haiti': 'HT',
        'cambodia': 'KH',
        'aruba': 'AW',
        'french polynesia': 'PF',
        'afghanistan': 'AF',
        'bermuda': 'BM',
        'guyana': 'GY',
        'armenia': 'AM',
        'malawi': 'MW',
        'antigua': 'AG',
        'rwanda': 'RW',
        'guernsey': 'GG',
        'the gambia': 'GM',
        'faroe islands': 'FO',
        'st. lucia': 'LC',
        'cayman islands': 'KY',
        'benin': 'BJ',
        'andorra': 'AD',
        'grenada': 'GD',
        'us virgin islands': 'VI',
        'belize': 'BZ',
        'saint vincent and the grenadines': 'VC',
        'mongolia': 'MN',
        'mozambique': 'MZ',
        'mali': 'ML',
        'angola': 'AO',
        'french guiana': 'GF',
        'uzbekistan': 'UZ',
        'djibouti': 'DJ',
        'burkina faso': 'BF',
        'monaco': 'MC',
        'togo': 'TG',
        'greenland': 'GL',
        'gabon': 'GA',
        'gibraltar': 'GI',
        'democratic republic of the congo': 'CD',
        'kyrgyzstan': 'KG',
        'papua new guinea': 'PG',
        'bhutan': 'BT',
        'saint kitts and nevis': 'KN',
        'swaziland': 'SZ',
        'lesotho': 'LS',
        'laos': 'LA',
        'liechtenstein': 'LI',
        'northern mariana islands': 'MP',
        'suriname': 'SR',
        'seychelles': 'SC',
        'british virgin islands': 'VG',
        'turks and caicos islands': 'TC',
        'dominica': 'DM',
        'mauritania': 'MR',
        'aland islands': 'AX',
        'san marino': 'SM',
        'sierra leone': 'SL',
        'niger': 'NE',
        'republic of the congo': 'CG',
        'anguilla': 'AI',
        'mayotte': 'YT',
        'cape verde': 'CV',
        'guinea': 'GN',
        'turkmenistan': 'TM',
        'burundi': 'BI',
        'tajikistan': 'TJ',
        'vanuatu': 'VU',
        'solomon islands': 'SB',
        'eritrea': 'ER',
        'samoa': 'WS',
        'american samoa': 'AS',
        'falkland islands': 'FK',
        'equatorial guinea': 'GQ',
        'tonga': 'TO',
        'comoros': 'KM',
        'palau': 'PW',
        'federated states of micronesia': 'FM',
        'central african republic': 'CF',
        'somalia': 'SO',
        'marshall islands': 'MH',
        'vatican city': 'VA',
        'chad': 'TD',
        'kiribati': 'KI',
        'sao tome and principe': 'ST',
        'tuvalu': 'TV',
        'nauru': 'NR',
        'réunion': 'RE'}
    return data.get(country, None)
