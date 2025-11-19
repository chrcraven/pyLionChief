"""
Copyright (c) Jordan Maxwell, All Rights Reserved.
See LICENSE file in the project root for full license information.
"""

import asyncio
import logging
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

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

async def discover_trains(retry: bool = False, max_retries: int = 10) -> list:
    """
    Scans for nearby Bluetooth devices with the LionChief service id and returns if found. If retry is True, the function will
    converted to a DroidConnection and added to a list to return. If retry is False, the function will out after a set
    period of time and return without discovering any trains.

    Args:
        retry (bool): whether or not to continue scanning until a device is found or the function is interrupted
        max_retries (int): maximum number of scan retry attempts (default: 10)

    Returns:
        a list of LionChiefConnection objects representing the discovered train Bluetooth devices if any. Otherwise an empty list
    """

    train_connections = []
    retry_count = 0
    backoff_delay = 1.0  # Start with 1 second delay

    while True:
        try:
            # Scan for devices with the LionChief service UUID
            logging.debug("Starting BLE scan for LionChief trains...")
            devices = await BleakScanner.discover(
                return_adv=True,
                service_uuids=[LionChiefConnection.LionChiefServiceId],
                timeout=5.0
            )

            if len(devices) == 0:
                if retry and retry_count < max_retries:
                    retry_count += 1
                    logging.warning(f"No trains discovered. Retrying ({retry_count}/{max_retries})...")
                    await asyncio.sleep(backoff_delay)
                    # Exponential backoff, capped at 8 seconds
                    backoff_delay = min(backoff_delay * 1.5, 8.0)
                    continue
                else:
                    logging.error("Train discovery failed - no devices found.")
                    break
            else:
                # Process discovered trains
                for ble_device, advertising_data in devices.values():
                    logging.info(f"Train successfully discovered: [ {ble_device} ]")
                    train_connections.append(LionChiefConnection(ble_device, advertising_data.manufacturer_data))
                break

        except BleakError as e:
            error_msg = str(e).lower()

            # Handle "Operation already in progress" error specifically
            if "operation already in progress" in error_msg or "busy" in error_msg:
                if retry and retry_count < max_retries:
                    retry_count += 1
                    logging.warning(f"Bluetooth adapter busy (operation already in progress). Waiting {backoff_delay:.1f}s before retry ({retry_count}/{max_retries})...")
                    await asyncio.sleep(backoff_delay)
                    # Exponential backoff, capped at 10 seconds for adapter busy errors
                    backoff_delay = min(backoff_delay * 2.0, 10.0)
                    continue
                else:
                    logging.error(f"BLE scan failed: {e}")
                    break
            else:
                # Handle other BleakErrors
                if retry and retry_count < max_retries:
                    retry_count += 1
                    logging.warning(f"BLE error occurred: {e}. Retrying ({retry_count}/{max_retries})...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(backoff_delay * 1.5, 8.0)
                    continue
                else:
                    logging.error(f"BLE scan failed: {e}")
                    break

        except Exception as e:
            # Catch any other unexpected errors
            logging.error(f"Unexpected error during train discovery: {e}")
            if retry and retry_count < max_retries:
                retry_count += 1
                logging.warning(f"Retrying after unexpected error ({retry_count}/{max_retries})...")
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 1.5, 8.0)
                continue
            else:
                break

    return train_connections

async def discover_train(retry: bool = False, max_retries: int = 10) -> LionChiefConnection:
    """
    Scans for nearby Bluetooth devices with the LionChief service id and returns if found. If retry is True, the function will
    continue scanning until it finds a device or is interrupted. If retry is False, the function will time out after a
    set period of time and return without discovering a device.

    Args:
        retry (bool): whether or not to continue scanning until a device is found or the function is interrupted
        max_retries (int): maximum number of scan retry attempts (default: 10)

    Returns:
        a LionChiefConnection object representing the discovered train Bluetooth device if any. Otherwise None
    """

    discovered_trains = await discover_trains(retry, max_retries)
    return None if len(discovered_trains) == 0 else discovered_trains[0]