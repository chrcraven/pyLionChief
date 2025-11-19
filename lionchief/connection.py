"""
Copyright (c) Jordan Maxwell, All Rights Reserved.
See LICENSE file in the project root for full license information.
"""

import asyncio
import logging
from bleak import BleakScanner, BleakClient

from lionchief.protocol import *
from lionchief.motor import LionChiefMotorController
from lionchief.sound import LionChiefSoundController
from lionchief.lighting import LionChiefLightingController

class LionChiefConnection(object):
    """
    Represents a connection to a LionChief train.
    """

    LionChiefServiceId = 'e20a39f4-73f5-4bc4-a12f-17d1ad07a961'

    def __init__(self, profile: str, manufacturer_data):
        """
        Initialize a LionChiefConnection object.

        Args:
            profile (str): The BLE profile of the train.
            manufacturer_data: The manufacturer data of the train.
        """
        
        self.profile = profile
        self.train = None
        self.manufacturer_data = manufacturer_data

        self.motor = LionChiefMotorController(self)
        self.sound = LionChiefSoundController(self)
        self.lighting = LionChiefLightingController(self)

    async def connect(self, silent: bool = False) -> None:
        """
        Connect to the LionChief train using BLE.
        """

        timeout = 0.0
        self.train = BleakClient(self.profile)
        await self.train.connect()

    async def disconnect(self, silent: bool = False) -> None:
        """
        Disconnect from the train.
        """

        if not self.train.is_connected:
            return

        logging.info("Disconnecting from train...")
        await self.send_train_command(LionChiefBluetoothCommands.Disconnect, [0, 0])
        await self.train.disconnect()

    async def send_train_command(self, command_id: int, values: list = []) -> None:
        """
        Send a command to the train.

        Args:
            command_id (int): The ID of the command.
            values (list): The values to be sent along with the command.
        """
        values.insert(0, command_id)

        checksum = 256
        for v in values:
            checksum -= v

        while checksum < 0:
            checksum += 256

        values.insert(0, 0)
        values.append(checksum)

        command = bytes(values)
        logging.debug('Sending command: %s' % command.hex())
        await self.train.write_gatt_char(LionChiefBluetoothCharacteristics.LionChiefWriteCharacteristic, command)

async def discover_trains(retry: bool = False) -> list:
    """
    Scans for nearby Bluetooth devices with the LionChief service id and returns if found. If retry is True, the function will
    converted to a DroidConnection and added to a list to return. If retry is False, the function will out after a set
    period of time and return without discovering any trains.

    Args:
        retry (bool): whether or not to continue scanning until a device is found or the function is interrupted

    Returns:
        a list of LionChiefConnection objects representing the discovered train Bluetooth devices if any. Otherwise an empty list
    """

    train_connections = []

    while True:
        # Scan for devices with the LionChief service UUID
        devices = await BleakScanner.discover(
            return_adv=True,
            service_uuids=[LionChiefConnection.LionChiefServiceId],
            timeout=5.0
        )

        if len(devices) == 0:
            if retry:
                logging.warning("Train discovery failed. Retrying...")
                await asyncio.sleep(1)
                continue
            else:
                logging.error("Train discovery failed.")
                break
        else:
            # Process discovered trains
            for ble_device, advertising_data in devices.values():
                logging.info(f"Train successfully discovered: [ {ble_device} ]")
                train_connections.append(LionChiefConnection(ble_device, advertising_data.manufacturer_data))
            break

    return train_connections

async def discover_train(retry: bool = False) -> LionChiefConnection:
    """
    Scans for nearby Bluetooth devices with the LionChief service id and returns if found. If retry is True, the function will
    continue scanning until it finds a device or is interrupted. If retry is False, the function will time out after a
    set period of time and return without discovering a device.

    Args:
        retry (bool): whether or not to continue scanning until a device is found or the function is interrupted

    Returns:
        a LionChiefConnection object representing the discovered train Bluetooth device if any. Otherwise None
    """

    discovered_trains = await discover_trains(retry)
    return None if len(discovered_trains) == 0 else discovered_trains[0]