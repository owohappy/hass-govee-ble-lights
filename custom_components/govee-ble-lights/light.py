from __future__ import annotations

from typing import Any



import logging

_LOGGER = logging.getLogger(__name__)



from enum import IntEnum

import time

import bleak_retry_connector



from bleak import BleakClient

from homeassistant.components import bluetooth

from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_EFFECT, ColorMode, LightEntity)



from .const import DOMAIN



UUID_CONTROL_CHARACTERISTIC = '00010203-0405-0607-0809-0a0b0c0d2b11'



class LedCommand(IntEnum):

    POWER      = 0x01

    BRIGHTNESS = 0x04

    COLOR      = 0x05

    EFFECT     = 0x06



class LedMode(IntEnum):

    MANUAL     = 0x02



async def async_setup_entry(hass, config_entry, async_add_entities):

    light = hass.data[DOMAIN][config_entry.entry_id]

    ble_device = bluetooth.async_ble_device_from_address(hass, light.address.upper(), False)

    async_add_entities([RGBPCBluetoothLight(light, ble_device)])



class RGBPCBluetoothLight(LightEntity):

    _attr_color_mode = ColorMode.RGB

    _attr_supported_color_modes = {ColorMode.RGB}

    _attr_supported_features = {"effect"}



    def __init__(self, light, ble_device) -> None:

        self._mac = light.address

        self._ble_device = ble_device

        self._state = None

        self._brightness = None

        self._effect = None



    @property

    def name(self) -> str:

        return "RGB-PC Light"



    @property

    def unique_id(self) -> str:

        return self._mac.replace(":", "")



    @property

    def brightness(self):

        return self._brightness



    @property

    def effect(self):

        return self._effect



    @property

    def is_on(self) -> bool | None:

        return self._state



    async def async_turn_on(self, **kwargs) -> None:

        await self._sendBluetoothData(LedCommand.POWER, [0x1])

        self._state = True



        if ATTR_BRIGHTNESS in kwargs:

            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)

            await self._sendBluetoothData(LedCommand.BRIGHTNESS, [brightness])

            self._brightness = brightness



        if ATTR_RGB_COLOR in kwargs:

            red, green, blue = kwargs.get(ATTR_RGB_COLOR)

            await self._sendBluetoothData(LedCommand.COLOR, [LedMode.MANUAL, red, green, blue])



        if ATTR_EFFECT in kwargs:

            effect = kwargs.get(ATTR_EFFECT)

            await self._sendBluetoothData(LedCommand.EFFECT, [effect])

            self._effect = effect



    async def async_turn_off(self, **kwargs) -> None:

        await self._sendBluetoothData(LedCommand.POWER, [0x0])

        self._state = False



    async def _connectBluetooth(self) -> BleakClient:

        client = await bleak_retry_connector.establish_connection(BleakClient, self._ble_device, self.unique_id)

        return client



    async def _sendBluetoothData(self, cmd, payload):

        if not isinstance(cmd, int):

            raise ValueError('Invalid command')

        if not isinstance(payload, bytes) and not (isinstance(payload, list) and all(isinstance(x, int) for x in payload)):

            raise ValueError('Invalid payload')

        if len(payload) > 17:

            raise ValueError('Payload too long')



        cmd = cmd & 0xFF

        payload = bytes(payload)

        frame = bytes([0x33, cmd]) + bytes(payload)

        frame += bytes([0] * (19 - len(frame)))



        checksum = 0

        for b in frame:

            checksum ^= b



        frame += bytes([checksum & 0xFF])

        client = await self._connectBluetooth()

        await client.write_gatt_char(UUID_CONTROL_CHARACTERISTIC, frame, False)
